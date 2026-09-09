"""Fetch new completed public PGNs separately from serial Stockfish review."""
import argparse
import io
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import chess.pgn

from scripts.continuation_common import ROOT, RUN, check_stop, digest, save
from scripts.feedback_matches_windows import feedback_path
from scripts.overnight_field_import import Links
from training.game_feedback import normalise_game

OUT = RUN/'field-01'


def fetch(url, path):
    check_stop()
    request=urllib.request.Request(url,headers={'User-Agent':'Chessity public game analysis',
                                               'Cache-Control':'no-cache'})
    with urllib.request.urlopen(request,timeout=30) as response:
        assert response.status==200
        data=response.read(4000001)
    assert len(data)<=4000000
    path.write_bytes(data)
    return data.decode('utf-8')


def download():
    check_stop()
    assert not OUT.exists()
    OUT.mkdir(parents=True)
    state=dict(status='fetching',code_sha256=digest(__import__('pathlib').Path(__file__)),
               observations=[],new_games=[],reviews=[],site_submission_verified=False)
    save(OUT/'state.json',state)
    try:
        ladder_url='https://aichessathon.com/leaderboard'
        ladder=fetch(ladder_url,OUT/'leaderboard.html')
        leaders=set(re.findall(r'data-href":"/team/([a-f0-9-]{36})[^}]{0,180}data-podium":1',
                               ladder.replace('\\','')))
        assert len(leaders)==1
        teams={'own':'b650ca5f-caff-48e7-932a-3ccdb6ab6332','leader':leaders.pop()}
        state['leader_evidence']=dict(url=ladder_url,sha256=digest(OUT/'leaderboard.html'),
            team_id=teams['leader'],observed_utc=datetime.now(timezone.utc).isoformat())
        previous=ROOT/'runs/overnight-20260909/field-01/source-manifest.json'
        known={r['url'] for r in json.loads(previous.read_text())['games']}
        state['prior_observations']={str(previous.relative_to(ROOT)):digest(previous)}
        for path in sorted((ROOT/'runs/daytime-20260909').glob('field-*/state.json')):
            old=json.loads(path.read_text())
            if old.get('status')!='complete':continue
            state['prior_observations'][str(path.relative_to(ROOT))]=digest(path)
            known.update(g['url'] for ob in old.get('observations',[]) for g in ob.get('games',[])
                         if g['status'] in ('downloaded','already_reviewed'))
        fetch('https://aichessathon.com/docs',OUT/'competition-docs.html')
        for label,team in teams.items():
            url='https://aichessathon.com/team/'+team+'?from=lb'
            path=OUT/(label+'.html')
            parser=Links()
            parser.feed(fetch(url,path))
            links=list(dict.fromkeys(urllib.parse.urlparse(p).path for p in parser.links
                if re.fullmatch(r'/game/[a-f0-9-]{36}',urllib.parse.urlparse(p).path)))[:12]
            assert links
            observation=dict(label=label,team_id=team,url=url,sha256=digest(path),games=[])
            state['observations'].append(observation)
            limit=8 if label=='own' else 3
            count=0
            for link in links:
                game_url='https://aichessathon.com'+link
                if game_url in known:
                    observation['games'].append(dict(url=game_url,status='already_reviewed'))
                    continue
                game_id=link.rsplit('/',1)[1]
                html=fetch(game_url,OUT/(label+'-'+game_id+'.html'))
                parsed=Links()
                parsed.feed(html)
                encoded=[p for p in parsed.links if p.startswith('data:application/x-chess-pgn;')]
                if not encoded:
                    observation['games'].append(dict(url=game_url,status='no_completed_pgn'))
                    continue
                assert len(encoded)==1
                pgn=urllib.parse.unquote(encoded[0].split(',',1)[1])
                game=chess.pgn.read_game(io.StringIO(pgn))
                assert game is not None and not game.errors
                if game.headers.get('Result') not in ('1-0','0-1','1/2-1/2'):
                    observation['games'].append(dict(url=game_url,status='unfinished_or_void'))
                    continue
                sides=re.findall(r'class="game-side" href="/team/([a-f0-9-]{36})',html)
                assert len(sides)==2 and team in sides
                record=dict(id=int(game.headers['Round']),source_game_id='chessathon:'+game_id,
                    candidate_white=sides[0]==team,pgn=pgn,
                    candidate_version='Public game; submission SHA256 unverified',
                    opponent=game.headers['Black' if sides[0]==team else 'White'],
                    termination=game.headers.get('Termination','unknown'))
                _,identity=normalise_game(record)
                record['score']=identity['score']
                board=game.end().board()
                record['final_fen']=board.fen()
                path=OUT/(label+'-'+game_id+'.pgn')
                path.write_text(pgn,encoding='utf-8',newline='\n')
                state['new_games'].append(dict(label=label,url=game_url,record=record))
                observation['games'].append(dict(url=game_url,status='downloaded',round=record['id'],
                    score=record['score'],sha256=digest(path),start_fen=game.board().fen(),
                    candidate_white=record['candidate_white'],opponent=record['opponent']))
                count+=1
                save(OUT/'state.json',state)
                if count>=limit:break
        for label in teams:
            records=[r['record'] for r in state['new_games'] if r['label']==label]
            save(OUT/(label+'-games.json'),dict(status='complete',games=records))
        state['status']='downloaded_awaiting_review'
    except BaseException as error:
        state.update(status='failed_download',error=repr(error))
        raise
    finally:
        state['downloaded_utc']=datetime.now(timezone.utc).isoformat()
        save(OUT/'state.json',state)
    print(json.dumps(dict(status=state['status'],new_games=[dict(label=r['label'],url=r['url'],
        round=r['record']['id'],score=r['record']['score'],white=r['record']['candidate_white'],
        opponent=r['record']['opponent']) for r in state['new_games']])),flush=True)


def review():
    check_stop()
    state=json.loads((OUT/'state.json').read_text())
    assert state['status']=='downloaded_awaiting_review' and not state['reviews']
    from scripts import feedback_batch
    from training import game_feedback
    from scripts.overnight_capacity import wait_for_capacity
    wait_for_capacity(OUT/'review-capacity.json',minimum_memory_mb=1400,wait_seconds=0)
    game_feedback.stop_check=check_stop
    state['status']='reviewing'
    save(OUT/'state.json',state)
    try:
        for label in ('own','leader'):
            check_stop()
            source=OUT/(label+'-games.json')
            records=json.loads(source.read_text())['games']
            if not records:continue
            sys.argv=['scripts.feedback_batch','--source',str(source),'--out',
                str(feedback_path(OUT/(label+'-review'))),'--initial-policy',
                str(ROOT/'runs/daytime-20260909/move-buffers-01/prototype/models/player-policy.npz')]
            feedback_batch.main()
            state['reviews'].append(dict(label=label,status='complete',games=len(records)))
            save(OUT/'state.json',state)
        state['status']='complete'
    except BaseException as error:
        state.update(status='failed_review',error=repr(error))
        raise
    finally:
        state['finished_utc']=datetime.now(timezone.utc).isoformat()
        save(OUT/'state.json',state)
    print(json.dumps(dict(status=state['status'],reviews=state['reviews'])),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('download','review'),required=True)
    {'download':download,'review':review}[parser.parse_args().mode]()
