"""Fresh own/current-leader PGNs followed by serial, history-aware feedback."""
import io
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import chess.pgn

from scripts.daytime_common import ROOT, RUN, check_stop, digest, save
from scripts.feedback_matches_windows import feedback_path
from scripts.overnight_field_import import Links
from training.game_feedback import normalise_game

OUT = RUN / 'field-05'
TEAMS = {'own': 'b650ca5f-caff-48e7-932a-3ccdb6ab6332'}


def fetch(url, destination):
    check_stop()
    request = urllib.request.Request(url, headers={
        'User-Agent': 'Chessity public-game preparation', 'Cache-Control': 'no-cache'})
    with urllib.request.urlopen(request, timeout=30) as response:
        assert response.status == 200
        data = response.read(4000001)
    assert len(data) <= 4000000
    destination.write_bytes(data)
    return data.decode('utf-8')


def run():
    assert not OUT.exists(), 'Preserve observations and reviews.'
    check_stop()
    OUT.mkdir(parents=True)
    state = dict(status='fetching', observations=[], reviews=[], new_games=[],
        source_sha256=digest(Path(__file__)), site_submission_verified=False)
    save(OUT / 'state.json', state)
    try:
        ladder_url = 'https://aichessathon.com/leaderboard'
        ladder = fetch(ladder_url, OUT / 'leaderboard.html')
        # React streaming escapes its table JSON. Inspect only the advertised
        # first-place row; page text is data, never executable instructions.
        plain = ladder.replace('\\', '')
        leaders = set(re.findall(r'data-href":"/team/([a-f0-9-]{36})[^}]{0,180}data-podium":1',plain))
        assert len(leaders)==1, 'Cannot identify a unique advertised leader; preserve the observation.'
        TEAMS['leader'] = leaders.pop()
        state['leader_evidence'] = dict(url=ladder_url, sha256=digest(OUT / 'leaderboard.html'),
            team_id=TEAMS['leader'], observed_utc=datetime.now(timezone.utc).isoformat())
        previous = json.loads((ROOT / 'runs/overnight-20260909/field-01/source-manifest.json').read_text())
        known = {r['url'] for r in previous['games']}
        state['prior_observations'] = {}
        for prior_path in (RUN/'field-03/state.json',RUN/'field-04/state.json'):
            if prior_path.exists():
                old = json.loads(prior_path.read_text())
                assert old['status']=='complete'
                state['prior_observations'][str(prior_path.relative_to(ROOT))] = digest(prior_path)
                known.update(g['url'] for observation in old.get('observations',[])
                    for g in observation['games'] if g['status'] in ('downloaded','already_reviewed'))
        for label, team in TEAMS.items():
            url = 'https://aichessathon.com/team/' + team + '?from=lb'
            page = OUT / (label + '.html')
            parser = Links()
            parser.feed(fetch(url, page))
            links = list(dict.fromkeys(urllib.parse.urlparse(p).path for p in parser.links
                if re.fullmatch(r'/game/[a-f0-9-]{36}', urllib.parse.urlparse(p).path)))[:4]
            assert len(links) >= 3
            observation = dict(label=label, team_id=team, url=url, sha256=digest(page), games=[])
            completed = 0
            for link in links:
                game_url = 'https://aichessathon.com' + link
                if game_url in known:
                    observation['games'].append(dict(url=game_url, status='already_reviewed'))
                    completed += 1
                    if completed == 3:
                        break
                    continue
                game_id = link.rsplit('/', 1)[1]
                html_path = OUT / (label + '-' + game_id + '.html')
                html = fetch(game_url, html_path)
                game_page = Links()
                game_page.feed(html)
                encoded = [p for p in game_page.links if p.startswith('data:application/x-chess-pgn;')]
                if not encoded:
                    observation['games'].append(dict(url=game_url, status='no_completed_pgn'))
                    continue
                assert len(encoded) == 1
                pgn = urllib.parse.unquote(encoded[0].split(',', 1)[1])
                game = chess.pgn.read_game(io.StringIO(pgn))
                assert game is not None and not game.errors
                if game.headers.get('Result') not in ('1-0', '0-1', '1/2-1/2'):
                    observation['games'].append(dict(url=game_url, status='unfinished_or_void'))
                    continue
                sides = re.findall(r'class="game-side" href="/team/([a-f0-9-]{36})', html)
                assert len(sides) == 2 and team in sides
                board = game.board()
                for node in game.mainline():
                    assert node.move in board.legal_moves
                    board.push(node.move)
                record = dict(id=int(game.headers['Round']), source_game_id='chessathon:' + game_id,
                    candidate_white=sides[0] == team, pgn=pgn, final_fen=board.fen(),
                    candidate_version='Public competition game; submission hash unverified',
                    opponent=game.headers['Black' if sides[0] == team else 'White'],
                    termination=game.headers['Termination'])
                _, identity = normalise_game(record)
                record['score'] = identity['score']
                pgn_path = OUT / (label + '-' + game_id + '.pgn')
                pgn_path.write_text(pgn, encoding='utf-8', newline='\n')
                state['new_games'].append(dict(label=label, record=record))
                observation['games'].append(dict(url=game_url, status='downloaded',
                    round=record['id'], score=record['score'], sha256=digest(pgn_path)))
                completed += 1
                if completed == 3:
                    break
            state['observations'].append(observation)
            save(OUT / 'state.json', state)
        state['status'] = 'reviewing'
        save(OUT / 'state.json', state)
        from scripts import feedback_batch
        from training import game_feedback
        game_feedback.stop_check = check_stop
        for label in TEAMS:
            records = [r['record'] for r in state['new_games'] if r['label'] == label]
            source = OUT / (label + '-games.json')
            save(source, dict(status='complete', games=records))
            if not records:
                continue
            check_stop()
            sys.argv = ['scripts.feedback_batch', '--source', str(source), '--out',
                str(feedback_path(OUT / (label + '-review'))), '--initial-policy',
                str(RUN / 'pawn-bitboards-01/prototype/models/player-policy.npz')]
            feedback_batch.main()
            state['reviews'].append(dict(label=label, status='complete', games=len(records)))
            save(OUT / 'state.json', state)
        state['status'] = 'complete'
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        state['finished_utc'] = datetime.now(timezone.utc).isoformat()
        save(OUT / 'state.json', state)
    print(json.dumps(dict(status=state['status'], new_games=len(state['new_games']), reviews=state['reviews'])))


if __name__ == '__main__':
    run()
