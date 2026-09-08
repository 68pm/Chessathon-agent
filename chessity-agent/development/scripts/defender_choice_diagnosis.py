"""Resolve the three possible defenses in a diagnosed checking continuation."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import manifest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/improvement-loop-20260907/cycle-33'


def stop_check():
    if any((ROOT / flag).exists() for flag in ['STOP_TRAINING', 'STOP_BENCHMARK']):
        raise InterruptedError('User stop flag')


def verify():
    prep = json.loads((OUT / 'preparation.json').read_text())
    assert manifest(ROOT / prep['candidate']) == prep['candidate_files']
    assert sha256(OUT / 'position.json') == prep['position_sha256']
    for name, digest in prep['source_files'].items():
        assert sha256(ROOT / name) == digest
    return prep


def restore(row):
    import chess

    board = chess.Board(row['start_fen'])
    for move in row['history']:
        board.push_uci(move)
    assert board.fen() == row['fen'] and board.is_valid()
    return board


def teacher():
    import chess

    from scripts.improvement_audit import evaluate
    from scripts.magnus_benchmark import SF
    from scripts.overnight_capacity import wait_for_capacity
    from training.puzzle_verifier import Verifier

    verify()
    path = OUT / 'teacher.json'
    assert not path.exists()
    position = json.loads((OUT / 'position.json').read_text())
    board = restore(position)
    assert board.turn == chess.WHITE and board.is_check()
    assert set(position['choices']) == {m.uci() for m in board.legal_moves}
    report = dict(status='running', position_sha256=sha256(OUT / 'position.json'),
        teacher_sha256=sha256(SF), newly_requested_nodes=0, budgets=[])
    save_json(path, report)
    wait_for_capacity(OUT / 'stockfish-capacity.json')
    verifier = Verifier(SF)
    try:
        for budget in [80000, 320000]:
            stop_check()
            best = evaluate(verifier.engine, board, budget)
            report['newly_requested_nodes'] += budget
            choices = []
            for uci in position['choices']:
                stop_check()
                move = chess.Move.from_uci(uci)
                value = best if best['pv'][0] == uci else evaluate(verifier.engine, board, budget, move)
                if best['pv'][0] != uci:
                    report['newly_requested_nodes'] += budget
                choices.append(dict(uci=uci, san=board.san(move), analysis=value))
            report['budgets'].append(dict(nodes=budget, best=best, choices=choices))
            save_json(path, report)
        assert report['newly_requested_nodes'] <= 1600000
        verify()
        report['status'] = 'complete'
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        verifier.close()
        save_json(path, report)


def student():
    prep = verify()
    path = OUT / 'student.json'
    assert not path.exists()
    result = dict(status='initializing', pid=os.getpid(), records=[],
        position_sha256=sha256(OUT / 'position.json'), preparation_sha256=sha256(OUT / 'preparation.json'))
    save_json(path, result)
    try:
        stop_check()
        base = ROOT / prep['candidate']
        sys.path.insert(0, str(base.resolve()))
        tick = time.perf_counter()
        import numpy as np

        import agent

        driver = sys.modules['engine.compiled_driver']
        arrays, core, decode = driver.arrays, driver.core, driver.decode
        assert Path(core.__file__).resolve() == (base / 'engine/compiled_core.py').resolve()
        result['init_seconds'] = time.perf_counter() - tick
        assert result['init_seconds'] <= 90
        search = agent._search
        search.policy = None
        position = json.loads((OUT / 'position.json').read_text())
        board_root = restore(position)

        def history(board):
            past, replay = [], board.copy(stack=True)
            for _ in range(min(board.halfmove_clock, len(board.move_stack)) + 1):
                p, s = arrays(replay)
                past.append(core.position_hash(p, s))
                if not replay.move_stack:
                    break
                replay.pop()
            past.reverse()
            hashes = np.zeros(800, dtype=np.uint64)
            hashes[:len(past)] = past
            return hashes, past, np.uint64(sum(map(int, past)) & ((1 << 64) - 1))

        for depth in [3, 5]:
            for uci in position['choices']:
                stop_check()
                board = board_root.copy(stack=True)
                san = board.san(next(m for m in board.legal_moves if m.uci() == uci))
                board.push_uci(uci)
                for name in ['ttkey', 'ttcontext', 'ttdata', 'killers', 'history']:
                    getattr(search, name).fill(0)
                p, s = arrays(board)
                old_p, old_s = p.copy(), s.copy()
                accumulator = core.build_accumulator(p, search.weights, search.bias)
                old_accumulator = accumulator.copy()
                hashes, past, context = history(board)
                control = np.array([0, 0, 250000], dtype=np.int64)
                tick = time.perf_counter()
                value = core.search(p, s, depth - 1, -31000, 31000, 6, 0, hashes, len(past), context,
                    search.ttkey, search.ttcontext, search.ttdata, search.killers, search.history,
                    control, tick + 4, search.weights, search.bias, search.output, search.blend,
                    search.conversion, search.reductions, accumulator, 0)
                elapsed = time.perf_counter() - tick
                assert np.array_equal(p, old_p) and np.array_equal(s, old_s)
                assert np.array_equal(accumulator, old_accumulator) and list(hashes[:len(past)]) == past
                assert int(control[0]) <= 250000 and elapsed <= 4.25
                row = dict(depth=depth, uci=uci, san=san, complete=not bool(control[1]),
                    score_white=-int(value) if not control[1] else None, nodes=int(control[0]), seconds=elapsed)
                if not control[1]:
                    pv, entries, stop = [uci], [], 'quiescence_reached'
                    for remaining in range(depth - 1, 0, -1):
                        if board.is_checkmate() or board.is_stalemate() or board.is_insufficient_material() or board.halfmove_clock >= 100 or board.is_repetition(3):
                            stop = 'terminal'
                            break
                        p, s = arrays(board)
                        key = core.position_hash(p, s)
                        slot = int(key) & (len(search.ttkey) - 1)
                        entry = search.ttdata[slot]
                        if not (search.ttkey[slot] == key and search.ttcontext[slot] == context
                                and entry[4] == board.halfmove_clock and entry[0] >= remaining and entry[2] == 0):
                            stop = 'missing_or_nonexact_transposition_entry'
                            break
                        move = decode(int(entry[3])) if entry[3] else None
                        if move not in board.legal_moves:
                            stop = 'missing_or_illegal_table_move'
                            break
                        entries.append(dict(uci=move.uci(), san=board.san(move), remaining=remaining,
                            stored_depth=int(entry[0]), stored_bound=int(entry[2])))
                        old_rights = board.castling_rights
                        board.push(move)
                        pv.append(move.uci())
                        p, s = arrays(board)
                        child_key = core.position_hash(p, s)
                        context = child_key if board.halfmove_clock == 0 or old_rights != board.castling_rights else np.uint64(
                            (int(context) + int(child_key)) & ((1 << 64) - 1))
                    p, s = arrays(board)
                    row['trace'] = dict(pv=pv, entries=entries, stop=stop, fen=board.fen(),
                        start_fen=board.root().fen(), history=[m.uci() for m in board.move_stack],
                        static_white=int(core.classical(p, s, search.conversion)) * (1 if board.turn else -1))
                result['records'].append(row)
                result['status'] = 'diagnosing'
                save_json(path, result)
        verify()
        assert len(result['records']) == 6
        result['status'] = 'complete'
    except BaseException as error:
        result.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(path, result)


def main():
    from scripts.improvement_king_coordination_gate import child
    from scripts.overnight_capacity import wait_for_capacity

    assert not (OUT / 'student.json').exists() and not (OUT / 'teacher.json').exists()
    for stage in ['teacher', 'student']:
        wait_for_capacity(OUT / (stage + '-capacity.json'))
        child(['-m', 'scripts.defender_choice_diagnosis', '--mode', stage], OUT / (stage + '.log'), timeout=360)
        assert json.loads((OUT / (stage + '.json')).read_text())['status'] == 'complete'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['teacher', 'student'])
    args = parser.parse_args()
    if args.mode:
        (teacher if args.mode == 'teacher' else student)()
    else:
        main()
