"""Bounded teacher verification of the continuations missed after correct Kh1."""
import argparse
import json
from pathlib import Path

from scripts.alien_rating_ladder import save_json, sha256

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/improvement-loop-20260907/cycle-34'


def stop_check():
    if any((ROOT / flag).exists() for flag in ['STOP_TRAINING', 'STOP_BENCHMARK']):
        raise InterruptedError('User stop flag')


def worker():
    import chess

    from scripts.improvement_audit import evaluate
    from scripts.magnus_benchmark import SF
    from scripts.overnight_capacity import wait_for_capacity
    from training.puzzle_verifier import Verifier

    path = OUT / 'teacher.json'
    assert not path.exists(), 'Preserve every diagnostic attempt'
    prep = json.loads((OUT / 'preparation.json').read_text())

    def verify():
        assert sha256(OUT / 'positions.jsonl') == prep['positions_sha256']
        for name, digest in prep['source_files'].items():
            assert sha256(ROOT / name) == digest

    verify()
    positions = [json.loads(line) for line in (OUT / 'positions.jsonl').read_text().splitlines()]
    assert len(positions) == 4
    report = dict(status='running', teacher_sha256=sha256(SF),
        preparation_sha256=sha256(OUT / 'preparation.json'), newly_requested_nodes=0, records=[])
    save_json(path, report)
    wait_for_capacity(OUT / 'stockfish-capacity.json')
    verifier = Verifier(SF)
    try:
        for row in positions:
            board = chess.Board(row['start_fen'])
            for move in row['history']:
                board.push_uci(move)
            assert board.fen() == row['fen'] and board.is_valid()
            assert all(chess.Move.from_uci(m) in board.legal_moves for m in row['student_choices'])
            for budget in [80000, 320000]:
                stop_check()
                best = evaluate(verifier.engine, board, budget)
                report['newly_requested_nodes'] += budget
                analyses = [('best', best)]
                for move in row['student_choices']:
                    stop_check()
                    value = best if best['pv'][0] == move else evaluate(verifier.engine, board, budget, chess.Move.from_uci(move))
                    if best['pv'][0] != move:
                        report['newly_requested_nodes'] += budget
                    analyses.append((move, value))
                records = []
                for label, value in analyses:
                    factor = 1 if board.turn else -1
                    line, replay = [], board.copy(stack=True)
                    for uci in value['pv']:
                        move = chess.Move.from_uci(uci)
                        line.append(replay.san(move))
                        replay.push(move)
                    records.append(dict(label=label, **value, cp_white=value['cp'] * factor if value['cp'] is not None else None,
                        mate_white=value['mate'] * factor if value['mate'] is not None else None, san=line))
                report['records'].append(dict(id=row['id'], budget=budget, analyses=records))
                save_json(path, report)
        assert report['newly_requested_nodes'] <= 3200000
        verify()
        report['status'] = 'complete'
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        verifier.close()
        save_json(path, report)


def main():
    from scripts.improvement_king_coordination_gate import child
    from scripts.overnight_capacity import wait_for_capacity

    assert not (OUT / 'teacher.json').exists()
    wait_for_capacity(OUT / 'worker-capacity.json')
    child(['-m', 'scripts.greedy_capture_refutations', '--worker'], OUT / 'teacher.log', timeout=360)
    assert json.loads((OUT / 'teacher.json').read_text())['status'] == 'complete'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    (worker if args.worker else main)()
