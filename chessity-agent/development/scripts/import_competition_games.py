"""Import browser-observed PGNs without confusing old and new submissions."""

import argparse
import csv
import io
import json
import re
from pathlib import Path

import chess
import chess.pgn

from scripts.alien_rating_ladder import save_json, sha256


def fnv1a(text):
    value = 2166136261
    for char in text:
        value = ((value ^ ord(char)) * 16777619) & 0xffffffff
    return f'{value:x}'


def restore_pgn(compact):
    headers = re.findall(r'\[\w+ "(?:[^"\\]|\\.)*"\]', compact)
    assert headers
    moves = compact[compact.rfind(']') + 1:].strip()
    def clock(match):
        ms = int(match[1])
        hours, ms = divmod(ms, 3600000)
        minutes, ms = divmod(ms, 60000)
        return f'{{ [%clk {hours}:{minutes:02}:{ms / 1000:06.3f}] }}'
    return '\n'.join(headers) + '\n\n' + re.sub(r'\{(\d+)\}', clock, moves) + '\n'


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--compact', type=Path, required=True)
    p.add_argument('--csv', type=Path, required=True)
    p.add_argument('--metadata', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise ValueError('Use a new import directory; preserve existing provenance.')
    metadata = json.loads(args.metadata.read_text())
    rows = json.loads(args.compact.read_text())
    with args.csv.open(encoding='utf-8-sig', newline='') as f:
        summary = {r['round']: r for r in csv.DictReader(f)}
    reports, exports = [], []
    for row in rows:
        info = metadata['games'][row['name']]
        assert fnv1a(row['compact']) == info['fnv1a32'] and len(row['compact']) == info['characters']
        assert Path(row['name']).name == row['name'] and row['name'].endswith('.pgn')
        text = restore_pgn(row['compact'])
        game = chess.pgn.read_game(io.StringIO(text))
        assert game and not game.errors
        board = game.board()
        assert board.is_valid()
        white = game.headers['White'] == metadata['team']
        assert white or game.headers['Black'] == metadata['team']
        clocks, records, own_elapsed = [120000, 120000], [], []
        own_clocks = []
        for node in game.mainline():
            move = node.move
            assert move in board.legal_moves and node.clock() is not None
            side = 0 if board.turn else 1
            clock_after = round(node.clock() * 1000)
            elapsed = clocks[side] + 500 - clock_after
            assert elapsed >= -2 and clock_after > 0
            records.append(dict(fen=board.fen(), uci=move.uci(), white=board.turn,
                                clock_before_ms=clocks[side], elapsed_ms=elapsed))
            if board.turn == white:
                own_elapsed.append(elapsed / 1000)
                own_clocks.append(clock_after)
            clocks[side] = clock_after
            board.push(move)
        assert board.result(claim_draw=True) == game.headers['Result']
        row_summary = summary['Rated ' + game.headers['Round']]
        assert len(own_elapsed) == int(row_summary['moves'])
        assert abs(sum(own_elapsed) - float(row_summary['time_used_s'])) < .11
        assert abs(own_clocks[-1] / 1000 - float(row_summary['clock_left_s'])) < .11
        result = game.headers['Result']
        score = .5 if result == '1/2-1/2' else float((result == '1-0') == white)
        expected = {'Win': 1., 'Draw': .5, 'Loss': 0.}[row_summary['result']]
        assert score == expected
        family = 'competition:' + info['game_id']
        reports.append(dict(id=int(game.headers['Round']), family=family, candidate_white=white,
            candidate_path=metadata['candidate_path'], candidate_version_inference=metadata['version_evidence'],
            score=score, opponent=game.headers['Black' if white else 'White'],
            start_fen=game.board().fen(), opening=[], moves=records, final_fen=board.fen(),
            termination=game.headers['Termination'], url=info['url'],
            own_moves=len(own_elapsed), own_elapsed_s=sum(own_elapsed),
            minimum_own_clock_s=min(own_clocks) / 1000, finished_utc=row_summary['finished_at']))
        exports.append((row['name'], text))
    args.out.mkdir(parents=True)
    for name, text in exports:
        (args.out / name).write_text(text, encoding='utf-8', newline='\n')
    save_json(args.out / 'results.json', dict(status='complete', games=reports,
        source='Authenticated dashboard DOM PGN links and downloaded all-game CSV',
        compact_sha256=sha256(args.compact), csv_sha256=sha256(args.csv),
        metadata_sha256=sha256(args.metadata), source_code_sha256=sha256(__file__),
        clock_config=dict(base_ms=120000, increment_ms=500),
        scope='Competition data with inferred version mapping. Not a locally scheduled or independently calibrated opponent match. No new training has occurred.'))
    save_json(args.out / 'import-review.json', dict(status='complete', games=len(reports),
        wins=sum(g['score'] == 1 for g in reports), draws=sum(g['score'] == .5 for g in reports),
        losses=sum(g['score'] == 0 for g in reports),
        legal_moves=sum(len(g['moves']) for g in reports), own_moves=sum(g['own_moves'] for g in reports),
        checked=['DOM compact checksums', 'PGN legality and outcome', 'per-move clocks',
                 'CSV own move counts, time used, result and final clock'],
        version_evidence=metadata['version_evidence'],
        pgn_format='Clock comments reconstructed from exact integer milliseconds; formatting normalized, source moves and clocks preserved.'))
    print(json.dumps(dict(games=len(reports), own_moves=sum(g['own_moves'] for g in reports),
                         outcomes=[g['score'] for g in reports])), flush=True)


if __name__ == '__main__':
    main()
