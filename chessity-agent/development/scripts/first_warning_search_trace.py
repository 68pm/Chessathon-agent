"""Bounded full-window diagnosis of all four new first-warning positions."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import manifest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/improvement-loop-20260907/cycle-30'


def stop_check():
    if any((ROOT / name).exists() for name in ['STOP_TRAINING', 'STOP_BENCHMARK']):
        raise InterruptedError('User stop flag')


def worker():
    path = OUT / 'trace.json'
    if path.exists():
        raise ValueError('Preserve every diagnostic attempt')
    prep = json.loads((OUT / 'preparation.json').read_text())
    candidate = ROOT / prep['candidate']

    def verify():
        assert manifest(candidate) == prep['candidate_files']
        assert sha256(OUT / 'roots.jsonl') == prep['roots_sha256']
        assert all(sha256(ROOT / name) == digest for name, digest in prep['source_files'].items())

    verify()
    roots = [json.loads(line) for line in (OUT / 'roots.jsonl').read_text().splitlines()]
    assert len(roots) == 4 and sum(len(row['choices']) for row in roots) == 9
    result = dict(status='initializing', pid=os.getpid(), records=[],
        preparation_sha256=sha256(OUT / 'preparation.json'), limits=dict(depths=[4, 6, 8],
            nodes_per_branch=500000, seconds_per_branch=8, branches=27, teacher_nodes=0))
    save_json(path, result)
    try:
        stop_check()
        sys.path.insert(0, str(candidate.resolve()))
        started = time.perf_counter()
        import chess
        import numpy as np

        import agent

        result['init_seconds'] = time.perf_counter() - started
        assert result['init_seconds'] <= 90
        driver = sys.modules['engine.compiled_driver']
        arrays, core = driver.arrays, driver.core
        assert Path(core.__file__).resolve() == (candidate / 'engine/compiled_core.py').resolve()
        search = agent._search
        search.policy = None
        result['status'] = 'diagnosing'
        save_json(path, result)
        for target in roots:
            position = chess.Board(target['start_fen'])
            for uci in target['history']:
                position.push_uci(uci)
            assert position.fen() == target['fen'] and position.is_valid()
            for depth in [4, 6, 8]:
                for forced in target['choices']:
                    stop_check()
                    board = position.copy(stack=True)
                    move = chess.Move.from_uci(forced)
                    assert move in board.legal_moves
                    san = board.san(move)
                    board.push(move)
                    for name in ['ttkey', 'ttcontext', 'ttdata', 'killers', 'history']:
                        getattr(search, name).fill(0)
                    pieces, state = arrays(board)
                    saved_pieces, saved_state = pieces.copy(), state.copy()
                    accumulator = core.build_accumulator(pieces, search.weights, search.bias)
                    saved_accumulator = accumulator.copy()
                    replay, past = board.copy(stack=True), []
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
                    control = np.array([0, 0, 500000], dtype=np.int64)
                    tick = time.perf_counter()
                    value = core.search(pieces, state, depth - 1, -31000, 31000, 1, 0,
                        hashes, len(past), context, search.ttkey, search.ttcontext, search.ttdata,
                        search.killers, search.history, control, tick + 8, search.weights,
                        search.bias, search.output, search.blend, search.conversion,
                        search.reductions, accumulator, 2)
                    elapsed = time.perf_counter() - tick
                    assert np.array_equal(pieces, saved_pieces) and np.array_equal(state, saved_state)
                    assert np.array_equal(accumulator, saved_accumulator)
                    assert list(hashes[:len(past)]) == past
                    assert int(control[0]) <= 500000 and elapsed <= 8.25
                    row = dict(id=target['id'], depth=depth, forced=forced, san=san,
                        complete=not bool(control[1]), score_root=-int(value) if not control[1] else None,
                        nodes=int(control[0]), seconds=elapsed,
                        static_root=-int(core.classical(pieces, state, search.conversion)))
                    result['records'].append(row)
                    save_json(path, result)
                    print(json.dumps(row), flush=True)
        verify()
        assert len(result['records']) == 27
        result['status'] = 'complete'
    except BaseException as error:
        result.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(path, result)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    if args.worker:
        worker()
    else:
        from scripts.improvement_king_coordination_gate import child
        from scripts.overnight_capacity import wait_for_capacity

        assert not (OUT / 'trace.json').exists()
        wait_for_capacity(OUT / 'capacity.json')
        child(['-m', 'scripts.first_warning_search_trace', '--worker'], OUT / 'trace.log', timeout=360)
        assert json.loads((OUT / 'trace.json').read_text())['status'] == 'complete'


if __name__ == '__main__':
    main()
