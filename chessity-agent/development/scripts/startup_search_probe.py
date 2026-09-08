"""One fresh-process position pass, with explicit initialization and wall-clock records."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from scripts.alien_rating_ladder import save_json, sha256


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--roots', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('Preserve every previous position pass.')
    state = dict(status='initializing', pid=os.getpid(), candidate=str(args.candidate),
        roots_sha256=sha256(args.roots), source_sha256=sha256(__file__),
        requested_seconds=1.0, maximum_wall_seconds=1.25, initialization_limit_seconds=90,
        results=[], scope='Exposed search diagnostic; root policy disabled equally. No rating or learning claim.')
    save_json(args.out, state)
    try:
        sys.path.insert(0, str(args.candidate.resolve()))
        tick = time.perf_counter()
        import chess

        import agent

        state['init_seconds'] = time.perf_counter() - tick
        assert state['init_seconds'] <= 90, 'Initialization exceeded competition budget'
        state['status'] = 'probing'
        save_json(args.out, state)
        rows = [json.loads(line) for line in args.roots.read_text().splitlines()]
        assert len(rows) == 17 and len({r['id'] for r in rows}) == 17
        search = agent._search
        search.policy = None
        for row in rows:
            if any((Path.cwd() / f).exists() for f in ['STOP_TRAINING', 'STOP_BENCHMARK']):
                raise InterruptedError('User stop flag')
            board = chess.Board(row['start_fen'])
            for uci in row['history']:
                board.push_uci(uci)
            assert board.fen() == row['fen']
            stack = list(board.move_stack)
            for name in ['ttkey', 'ttcontext', 'ttdata', 'killers', 'history']:
                getattr(search, name).fill(0)
            tick = time.perf_counter()
            result = search.run(board, 1.0, 1.0, max_nodes=2**60, max_depth=64)
            wall = time.perf_counter() - tick
            assert board.fen() == row['fen'] and board.move_stack == stack
            assert result.move in board.legal_moves
            state['results'].append(dict(id=row['id'], fen=row['fen'], original_move=row['played'],
                uci=result.move.uci(), depth=result.depth, nodes=result.nodes, seconds=result.elapsed,
                wall_seconds=wall, score=result.score, iterations=getattr(search, 'iterations', None),
                agrees_with_deep_teacher=result.move.uci() == row['verification'][-1]['best']['pv'][0],
                repeats_large_error=result.move.uci() == row['played']))
            save_json(args.out, state)
            assert result.depth >= 1 and wall <= 1.25, 'Position pass exceeded declared operational bound'
        state['status'] = 'complete'
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(args.out, state)
    print(json.dumps(dict(status=state['status'], init_seconds=state['init_seconds'],
        positions=len(state['results']))), flush=True)


if __name__ == '__main__':
    main()
