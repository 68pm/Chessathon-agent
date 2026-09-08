"""Resolve the screened 2400 discontinuity and the early 2600 deterioration."""
import json
import os

import chess

from scripts.alien_rating_ladder import save_json, sha256
from scripts.improvement_audit import evaluate
from scripts.magnus_benchmark import SF
from scripts.overnight_capacity import wait_for_capacity
from training.fastchess_data import ROOT
from training.puzzle_verifier import Verifier

OUT = ROOT / 'runs/e55-loss-draw-review-20260908'
IDS = ['game-002-ply-021', 'game-002-ply-023', 'game-002-ply-025', 'game-004-ply-011']


def main():
    assert json.loads((OUT / 'context.json').read_text())['status'] == 'complete'
    path = OUT / 'transition-review.json'
    assert not path.exists()
    rows = {r['id']: r for r in map(json.loads, (OUT / 'audit/positions.jsonl').read_text().splitlines())}
    state = dict(status='running', pid=os.getpid(), ids=IDS, budgets=[80000, 320000, 1280000],
        maximum_requested_nodes=13440000, requested_nodes=0, records=[],
        source_sha256=sha256(__file__), audit_sha256=sha256(OUT / 'audit/positions.jsonl'),
        teacher_sha256=sha256(SF), reason='20k screening missed a379cp inter-turn drop after20...Qxc6; inspect its predecessor and reply plus14...Na4 before the2600 loss.')
    save_json(path, state)
    wait_for_capacity(OUT / 'transition-capacity.json')
    teacher = Verifier(SF)
    try:
        for uid in IDS:
            row = rows[uid]
            board = chess.Board(row['start_fen'])
            for move in row['history']:
                board.push_uci(move)
            assert board.fen() == row['fen']
            values = []
            for budget in state['budgets']:
                analyses = []
                for move in [None, chess.Move.from_uci(row['played'])]:
                    if any((ROOT / f).exists() for f in ['STOP_TRAINING', 'STOP_BENCHMARK']):
                        raise InterruptedError('User stop flag')
                    state['requested_nodes'] += budget
                    assert state['requested_nodes'] <= state['maximum_requested_nodes']
                    save_json(path, state)
                    analyses.append(evaluate(teacher.engine, board, budget, move))
                values.append(dict(best=analyses[0], played=analyses[1]))
            state['records'].append(dict(**{k: row[k] for k in ['id', 'fen', 'history', 'start_fen', 'played', 'game_id']}, verification=values))
            save_json(path, state)
        state['status'] = 'complete'
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        teacher.close()
        save_json(path, state)


if __name__ == '__main__':
    main()
