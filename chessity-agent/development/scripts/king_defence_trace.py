"""Bounded forced-branch diagnosis with exact-table PV provenance and leaf review."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import manifest

ROOT = Path(__file__).resolve().parents[1]


def stop_check():
    if any((ROOT / flag).exists() for flag in ['STOP_TRAINING', 'STOP_BENCHMARK']):
        raise InterruptedError('User stop flag')


def student(out):
    path = out / 'student.json'
    if path.exists():
        raise ValueError('Preserve earlier diagnosis')
    base = ROOT / 'candidates/compiled-startup-plain-v1'
    roots = ROOT / 'runs/improvement-loop-20260907/cycle-20/roots.jsonl'
    target = next(r for r in map(json.loads, roots.read_text().splitlines())
                  if r['id'] == 'startup19-game-001-ply-062')
    before = manifest(base)
    result = dict(status='initializing', pid=os.getpid(), files=before, roots_sha256=sha256(roots),
        source_sha256=sha256(__file__), target=target, records=[], leaves=[],
        limits=dict(depths=[4, 6, 8], branches=['g1f1', 'g1g2'], branch_nodes=750000,
            branch_seconds=15, leaf_nodes=250000, leaf_seconds=3),
        scope='Diagnostic forced branches and exact-table traces; no model update, strength gate or rating.')
    save_json(path, result)
    try:
        sys.path.insert(0, str(base.resolve()))
        started = time.perf_counter()
        import chess
        import numpy as np

        import agent

        # The agent must configure diagnostics before importing/compiling Numba.
        driver = sys.modules['engine.compiled_driver']
        arrays, core, decode = driver.arrays, driver.core, driver.decode
        assert Path(core.__file__).resolve() == (base / 'engine/compiled_core.py').resolve()
        result['init_seconds'] = time.perf_counter() - started
        assert result['init_seconds'] <= 90
        search = agent._search
        search.policy = None
        position = chess.Board(target['start_fen'])
        for uci in target['history']:
            position.push_uci(uci)
        assert position.fen() == target['fen']

        def clear():
            for name in ['ttkey', 'ttcontext', 'ttdata', 'killers', 'history']:
                getattr(search, name).fill(0)

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
            context = np.uint64(sum(map(int, past)) & ((1 << 64) - 1))
            return hashes, past, context

        def evaluate(board, depth, ply, nodes, seconds):
            clear()
            pieces, state = arrays(board)
            saved_pieces, saved_state = pieces.copy(), state.copy()
            accumulator = core.build_accumulator(pieces, search.weights, search.bias)
            saved_accumulator = accumulator.copy()
            hashes, past, context = history(board)
            control = np.array([0, 0, nodes], dtype=np.int64)
            started = time.perf_counter()
            value = core.search(pieces, state, depth, -31000, 31000, ply, 0,
                hashes, len(past), context, search.ttkey, search.ttcontext, search.ttdata,
                search.killers, search.history, control, started + seconds, search.weights,
                search.bias, search.output, search.blend, search.conversion, search.reductions, accumulator)
            elapsed = time.perf_counter() - started
            assert np.array_equal(pieces, saved_pieces) and np.array_equal(state, saved_state)
            assert np.array_equal(accumulator, saved_accumulator) and list(hashes[:len(past)]) == past
            factor = 1 if board.turn == position.turn else -1
            return dict(complete=not bool(control[1]), score_root=int(value) * factor if not control[1] else None,
                nodes=int(control[0]), seconds=elapsed, static_root=int(core.classical(pieces, state, search.conversion)) * factor)

        leaves = {}
        for depth in [4, 6, 8]:
            for forced in ['g1f1', 'g1g2']:
                stop_check()
                board = position.copy(stack=True)
                board.push_uci(forced)
                record = dict(depth=depth, forced=forced, analysis=evaluate(board, depth - 1, 1, 750000, 15))
                if record['analysis']['complete']:
                    pv, stop = [forced], 'main_depth_reached'
                    for remaining in range(depth - 1, 0, -1):
                        if board.outcome(claim_draw=True):
                            stop = 'terminal'
                            break
                        p, s = arrays(board)
                        key = core.position_hash(p, s)
                        _, _, context = history(board)
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
                        pv.append(move.uci())
                        board.push(move)
                    leaf_key = json.dumps([board.root().fen(), [m.uci() for m in board.move_stack]])
                    if leaf_key not in leaves:
                        p, s = arrays(board)
                        factor = 1 if board.turn == position.turn else -1
                        leaves[leaf_key] = dict(id=f'leaf-{len(leaves)+1:02}', start_fen=board.root().fen(),
                            history=[m.uci() for m in board.move_stack], fen=board.fen(), root_white=position.turn,
                            static_root=int(core.classical(p, s, search.conversion)) * factor,
                            main_depth_trace_complete=stop == 'main_depth_reached')
                    record['trace'] = dict(pv=pv, stop=stop, leaf_id=leaves[leaf_key]['id'])
                result['records'].append(record)
                result.update(status='tracing', leaves=list(leaves.values()))
                save_json(path, result)
                print(json.dumps(record), flush=True)
        for leaf in leaves.values():
            stop_check()
            board = chess.Board(leaf['start_fen'])
            for uci in leaf['history']:
                board.push_uci(uci)
            if board.outcome(claim_draw=True):
                leaf['terminal'] = board.outcome(claim_draw=True).termination.name.lower()
            else:
                leaf['quiescence'] = evaluate(board, 0, len(board.move_stack) - len(position.move_stack), 250000, 3)
            result['leaves'] = list(leaves.values())
            save_json(path, result)
        assert manifest(base) == before
        result['status'] = 'complete'
    except BaseException as error:
        result.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(path, result)


def teacher(out):
    import chess

    from scripts.improvement_audit import evaluate
    from scripts.magnus_benchmark import SF
    from training.puzzle_verifier import Verifier

    path = out / 'teacher.json'
    if path.exists():
        raise ValueError('Preserve teacher diagnosis')
    source = json.loads((out / 'student.json').read_text())
    assert source['status'] == 'complete' and len(source['leaves']) <= 6
    report = dict(status='running', source_sha256=sha256(out / 'student.json'), teacher_sha256=sha256(SF),
        budgets=[80000, 320000], newly_requested_nodes=0, effective_residual_cap_cp=125, leaves=[],
        scope='Finite teacher estimates for diagnosed endpoints; not accepted training labels or proof of a whole-game repair.')
    save_json(path, report)
    verifier = Verifier(SF)
    try:
        for leaf in source['leaves']:
            stop_check()
            board = chess.Board(leaf['start_fen'])
            for uci in leaf['history']:
                board.push_uci(uci)
            assert board.fen() == leaf['fen']
            item = dict(leaf)
            if not board.outcome(claim_draw=True):
                values = []
                for budget in report['budgets']:
                    value = evaluate(verifier.engine, board, budget)
                    factor = 1 if board.turn == leaf['root_white'] else -1
                    value['cp_root'] = value['cp'] * factor if value['cp'] is not None else None
                    value['mate_root'] = value['mate'] * factor if value['mate'] is not None else None
                    values.append(value)
                    report['newly_requested_nodes'] += budget
                item['teacher'] = values
                score = leaf.get('quiescence', {}).get('score_root')
                item['quiescence_minus_teacher_cp'] = [score - v['cp_root'] if score is not None and v['cp_root'] is not None else None for v in values]
            report['leaves'].append(item)
            save_json(path, report)
        report['status'] = 'complete'
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        verifier.close()
        save_json(path, report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['student', 'teacher'])
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    (student if args.mode == 'student' else teacher)(args.out)
