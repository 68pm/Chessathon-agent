"""Import only public completed competition games, retaining clocks and attribution."""

import io
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser

import chess.pgn

from scripts.overnight_geometry_trial import ROOT, check_stop, digest, save
from training.game_feedback import normalise_game

OUT = ROOT / 'runs/overnight-20260909/field-01'
TEAMS = {'own': ('b650ca5f-caff-48e7-932a-3ccdb6ab6332', 'The Veritys'),
         'leader': ('10021bb5-71a5-4b10-bde5-14e1f667501a', 'PSL God Matt Bomer')}


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            href = dict(attrs).get('href', '')
            if href not in self.links:
                self.links.append(href)


def run():
    assert not (OUT / 'source-manifest.json').exists(), 'Preserve finished import'
    provenance, records = [], {'own': [], 'leader': []}
    for label, (team_id, team_name) in TEAMS.items():
        parser = Links()
        parser.feed((OUT / f'{label}.html').read_text(encoding='utf-8'))
        paths = [urllib.parse.urlparse(p).path for p in parser.links]
        links = [p for p in paths if re.fullmatch(r'/game/[a-f0-9-]{36}', p)][:3]
        assert len(links) == 3
        for number, link in zip((75, 74, 73), links, strict=True):
            check_stop()
            source = OUT / f'{label}-{number}.html'
            if not source.exists():
                source.write_bytes(urllib.request.urlopen('https://aichessathon.com' + link,
                    timeout=40).read())
            page = Links()
            page.feed(source.read_text(encoding='utf-8'))
            pgndata = [p for p in page.links if p.startswith('data:application/x-chess-pgn;')]
            assert len(pgndata) == 1
            pgn = urllib.parse.unquote(pgndata[0].split(',', 1)[1])
            game = chess.pgn.read_game(io.StringIO(pgn))
            assert game and not game.errors and int(game.headers['Round']) == number
            # Public team names are data, never code or instructions.
            white, black = game.headers['White'], game.headers['Black']
            if label == 'own':
                assert team_name in (white, black)
            else:
                # Visible agent names can differ from historical PGN team names.
                # The public game-side links are ordered white then black.
                text = source.read_text(encoding='utf-8')
                sides = re.findall(r'class="game-side" href="/team/([a-f0-9-]{36})', text)
                assert len(sides) == 2 and team_id in sides
                team_name = white if sides[0] == team_id else black
            own_white = white == team_name
            board, clocks, own_elapsed = game.board(), {True: 120., False: 120.}, []
            for node in game.mainline():
                assert node.move in board.legal_moves and node.clock() is not None
                elapsed = clocks[board.turn] + .5 - node.clock()
                assert elapsed >= -.002 and node.clock() > 0
                if board.turn == own_white:
                    own_elapsed.append(elapsed)
                clocks[board.turn] = node.clock()
                board.push(node.move)
            assert game.headers['Result'] != '*'
            if game.headers['Termination'] in ('checkmate', 'threefold_repetition', 'fifty_moves', 'stalemate',
                                               'insufficient_material'):
                assert board.result(claim_draw=True) == game.headers['Result']
            record = dict(id=number, source_game_id='chessathon:' + link.rsplit('/', 1)[1],
                candidate_white=own_white, pgn=pgn, final_fen=board.fen(),
                candidate_version=('competition upload unverified for round; last observed active archive v1.41'
                                   if label == 'own' else 'public leader build, source unavailable'),
                opponent=black if own_white else white, termination=game.headers['Termination'])
            _, identity = normalise_game(record)
            record['score'] = identity['score']
            destination = OUT / f'{label}-{number}.pgn'
            destination.write_text(pgn, encoding='utf-8', newline='\n')
            records[label].append(record)
            provenance.append(dict(label=label, round=number, url='https://aichessathon.com' + link,
                html_sha256=digest(source), pgn_sha256=digest(destination), own_white=own_white,
                score=record['score'], opponent=record['opponent'], termination=record['termination'],
                plies=len(board.move_stack), own_moves=len(own_elapsed), own_seconds=sum(own_elapsed),
                final_own_clock=clocks[own_white], candidate_version=record['candidate_version']))
    for label, games in records.items():
        save(OUT / f'{label}-games.json', dict(status='complete', games=games))
    save(OUT / 'source-manifest.json', dict(downloaded_utc=datetime.now(timezone.utc).isoformat(),
        source_code_sha256=digest(__import__('pathlib').Path(__file__)), games=provenance,
        source='Unauthenticated public HTML PGN download links; only completed rounds73–75',
        version_warning='No per-game submission archive hash available; never assign these games to v1.53.'))
    print(json.dumps(provenance, indent=2), flush=True)


if __name__ == '__main__':
    run()
