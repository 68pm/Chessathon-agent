"""Diagnose the rook regression with bounded full-window forced branches."""
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--variant', choices=['baseline', 'prototype'], required=True)
    args = parser.parse_args()
    out = ROOT / 'runs/improvement-loop-20260907/cycle-24'
    path = out / (args.variant + '.json')
    if path.exists():
        raise ValueError('Preserve every diagnostic attempt')
    preparation = json.loads((out / 'preparation.json').read_text())
    for name, digest in preparation['source_files'].items():
        assert sha256(ROOT / name) == digest
    candidate = ROOT / preparation['candidates'][args.variant]['path']
    before = manifest(candidate)
    assert before == preparation['candidates'][args.variant]['files']
    roots = ROOT / 'runs/improvement-loop-20260907/cycle-20/roots.jsonl'
    assert sha256(roots) == preparation['roots_sha256']
    target = next(r for r in map(json.loads, roots.read_text().splitlines())
                  if r['id'] == 'startup19-game-003-ply-068')
    result = dict(status='initializing', variant=args.variant, pid=os.getpid(),
        candidate=str(candidate), files=before, target=target, records=[],
        preparation_sha256=sha256(out / 'preparation.json'), source_sha256=sha256(__file__),
        limits=dict(depths=[5, 6, 7], moves=['d8c8', 'd8d3', 'c3d1', 'c3d5'],
            nodes_per_branch=500000, seconds_per_branch=8, initialization_seconds=90),
        scope='Forced full-window diagnosis; not repeated clock tests, a promotion gate, training or Elo.')
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
        credits = [2] if args.variant == 'prototype' else []
        position = chess.Board(target['start_fen'])
        for uci in target['history']:
            position.push_uci(uci)
        assert position.fen() == target['fen'] and position.is_valid()
        result['status'] = 'diagnosing'
        save_json(path, result)
        for depth in [5, 6, 7]:
            for forced in ['d8c8', 'd8d3', 'c3d1', 'c3d5']:
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
                    search.reductions, accumulator, *credits)
                elapsed = time.perf_counter() - tick
                assert np.array_equal(pieces, saved_pieces) and np.array_equal(state, saved_state)
                assert np.array_equal(accumulator, saved_accumulator)
                assert list(hashes[:len(past)]) == past
                assert int(control[0]) <= 500000 and elapsed <= 8.25
                # One root move was forced, so the returned side-to-move score is negated.
                record = dict(depth=depth, forced=forced, san=san, complete=not bool(control[1]),
                    score_root=-int(value) if not control[1] else None, nodes=int(control[0]),
                    seconds=elapsed, static_root=-int(core.classical(pieces, state, search.conversion)))
                result['records'].append(record)
                save_json(path, result)
                print(json.dumps(record), flush=True)
        assert manifest(candidate) == before
        for name, digest in preparation['source_files'].items():
            assert sha256(ROOT / name) == digest
        result['status'] = 'complete'
    except BaseException as error:
        result.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(path, result)


if __name__ == '__main__':
    main()
