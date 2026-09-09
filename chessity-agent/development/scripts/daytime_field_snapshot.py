"""Refresh public team pages and download only newly observed completed game PGNs."""
import io
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import chess.pgn

from scripts.daytime_common import ROOT, check_stop, digest, save
from scripts.overnight_field_import import Links, TEAMS
from training.game_feedback import normalise_game

OUT = ROOT / 'runs/daytime-20260909/field-01'
OLD = ROOT / 'runs/overnight-20260909/field-01'


def fetch(url, path):
    check_stop()
    request = urllib.request.Request(url, headers={'User-Agent':'Chessity public-game preparation', 'Cache-Control':'no-cache'})
    with urllib.request.urlopen(request, timeout=30) as response:
        assert response.status == 200
        path.write_bytes(response.read())
    return path.read_text(encoding='utf-8')


def main():
    assert not OUT.exists(), 'Preserve each public observation.'
    OUT.mkdir(parents=True)
    previous = json.loads((OLD / 'source-manifest.json').read_text())
    old_urls = {row['url'] for row in previous['games']}
    result = dict(status='running', observations=[], new_games=[], review_summary=[])
    save(OUT / 'state.json', result)
    for label, (team_id, _) in TEAMS.items():
        url = 'https://aichessathon.com/team/' + team_id + '?from=lb'
        path = OUT / (label + '.html')
        text = fetch(url, path)
        parser = Links()
        parser.feed(text)
        links = [link for link in parser.links if re.fullmatch(r'/game/[a-f0-9-]{36}', link)][:3]
        assert len(links) == 3
        observation = dict(label=label,url=url,html_sha256=digest(path),latest_links=links,new=[])
        for link in links:
            game_url = 'https://aichessathon.com' + link
            if game_url in old_urls:
                continue
            game_id = link.rsplit('/',1)[1]
            game_path = OUT / (label + '-' + game_id + '.html')
            html = fetch(game_url, game_path)
            page = Links()
            page.feed(html)
            encoded = [p for p in page.links if p.startswith('data:application/x-chess-pgn;')]
            if not encoded:
                observation['new'].append(dict(url=game_url,status='no_completed_pgn'))
                continue
            assert len(encoded) == 1
            pgn = urllib.parse.unquote(encoded[0].split(',',1)[1])
            game = chess.pgn.read_game(io.StringIO(pgn))
            assert game is not None and not game.errors
            if game.headers['Result'] == '*':
                observation['new'].append(dict(url=game_url,status='unfinished'))
                continue
            sides = re.findall(r'class="game-side" href="/team/([a-f0-9-]{36})', html)
            assert len(sides) == 2 and team_id in sides
            board = game.board()
            for node in game.mainline():
                assert node.move in board.legal_moves
                board.push(node.move)
            record = dict(id=int(game.headers['Round']),source_game_id='chessathon:'+game_id,
                candidate_white=sides[0] == team_id,pgn=pgn,final_fen=board.fen(),
                candidate_version='Public competition game; submission archive hash unverified',
                opponent=game.headers['Black' if sides[0] == team_id else 'White'],
                termination=game.headers['Termination'])
            _, identity = normalise_game(record)
            record['score'] = identity['score']
            output = OUT / (label + '-' + game_id + '.pgn')
            output.write_text(pgn,encoding='utf-8',newline='\n')
            result['new_games'].append(dict(label=label,record=record))
            observation['new'].append(dict(url=game_url,status='downloaded_complete',
                round=record['id'],pgn_sha256=digest(output),score=record['score']))
        result['observations'].append(observation)
        folder = OLD / ('review' if label == 'own' else 'leader-review')
        docs = [json.loads(p.read_text()) for p in sorted(folder.glob('games/*/review.json'))]
        assert len(docs) == 3 and all(d['status'] == 'complete' for d in docs)
        negative = [dict(ply=r['ply'],san=r['san'],fen=r['fen'],tags=r['tags'],reward=r['reward'],
            best=[v['best'] for v in r['labels']],played=[v['played'] for v in r['labels']])
            for d in docs for r in d['rows'] if r['reward'] < 0]
        result['review_summary'].append(dict(label=label,already_reviewed_games=3,
            own_moves=sum(d['own_moves'] for d in docs),positive=sum(d['rewarded'] for d in docs),
            negative=sum(d['penalised'] for d in docs),largest_corrections=sorted(negative,key=lambda r:r['reward'])[:4]))
        save(OUT / 'state.json',result)
    for label in TEAMS:
        games = [g['record'] for g in result['new_games'] if g['label'] == label]
        save(OUT / (label+'-games.json'),dict(status='complete',games=games))
    result.update(status='complete',observed_utc=datetime.now(timezone.utc).isoformat(),
        source_sha256=digest(Path(__file__)),live_submission_verified=False,
        note='Previously downloaded/reviewed games reused without new teacher cost. New games require feedback before fitting.')
    save(OUT / 'state.json',result)
    print(json.dumps(dict(status='complete',new_games=len(result['new_games']),
        previous_reviewed_moves=sum(r['own_moves'] for r in result['review_summary']))),flush=True)


if __name__ == '__main__':
    main()
