"""Replay an exposed missed conversion with actual history and tablebase defence."""

import hashlib
import json

import chess

from experiments.elementary_endgames import ElementaryEndgames
from scripts.alien_rating_ladder import save_json, sha256
from training.fastchess_data import ROOT


def defend(board, tables):
    choices = []
    for move in list(board.legal_moves):
        board.push(move)
        outcome = board.outcome(claim_draw=True)
        if outcome:
            value, delay = (3 if outcome.winner is not None else 0), 0
        else:
            value = -tables.probe_wdl(board)
            delay = abs(tables.probe_dtz(board)) if value < 0 else 0
        board.pop()
        choices.append(((value, delay), move))
    return max(choices, key=lambda row: row[0])[1]


def main():
    root = ROOT / 'runs/improvement-loop-20260907'
    source = root / 'confirmation-01/rated-error-audit/positions.jsonl'
    row = next(row for row in map(json.loads, source.read_text(encoding='utf-8').splitlines())
               if row['id'] == 'game-012-ply-100')
    board = chess.Board(row['start_fen'])
    for uci in row['history']:
        board.push_uci(uci)
    assert board.fen() == row['fen']
    assert len(board.move_stack) == 100 and board.turn == chess.BLACK
    initial, history = board.fen(), list(row['history'])
    tables = ROOT / 'data/rook-bishop-syzygy-v1'
    helper = ElementaryEndgames(tables, max_pieces=5)
    records = []
    try:
        for ply in range(400):
            if board.is_game_over(claim_draw=True):
                break
            before = board.fen()
            if board.turn == chess.BLACK:
                move = helper.choose(board)
            else:
                move = defend(board, helper.tables)
            assert move in board.legal_moves and board.fen() == before
            records.append(dict(ply=ply, fen=before, uci=move.uci(), san=board.san(move)))
            board.push(move)
        assert records[0]['uci'] == 'd4f6'
        assert board.is_checkmate() and board.outcome().winner == chess.BLACK
    finally:
        helper.close()
    report = dict(status='complete', source_sha256=sha256(source), source_position_id=row['id'],
                  initial_fen=initial, actual_history=history, moves=records,
                  final_fen=board.fen(), result=board.result(), termination='checkmate',
                  plies=len(records), table_manifest_sha256=sha256(tables / 'manifest.json'),
                  helper_sha256=sha256(ROOT / 'experiments/elementary_endgames.py'),
                  script_sha256=hashlib.sha256(open(__file__, 'rb').read()).hexdigest(),
                  scope='Exposed development conversion drill, with full recorded history and WDL/DTZ-maximising losing defence. This is not an ordinary-game victory over the nominal 2600 opponent.')
    save_json(root / 'rook-bishop-conversion-probe.json', report)
    print(json.dumps({k: v for k, v in report.items() if k not in ['actual_history', 'moves']}))


if __name__ == '__main__':
    main()
