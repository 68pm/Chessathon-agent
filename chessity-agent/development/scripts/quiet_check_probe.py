"""Cycle21 clock roots plus three explicitly separate fixed-node diagnostics."""
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
        raise ValueError('Single-use probe: preserve every outcome')
    report = dict(status='initializing', pid=os.getpid(), roots_sha256=sha256(args.roots),
        source_sha256=sha256(__file__), candidate=str(args.candidate), results=[],
        scope='Exposed development roots; fixed-node and clock results kept separate, policy disabled equally.')
    save_json(args.out, report)
    try:
        sys.path.insert(0, str(args.candidate.resolve()))
        started = time.perf_counter()
        import chess

        import agent

        report['init_seconds'] = time.perf_counter() - started
        assert report['init_seconds'] <= 90, 'Initialization exceeded competition budget'
        report['status'] = 'probing'
        save_json(args.out, report)
        rows = [json.loads(line) for line in args.roots.read_text().splitlines()]
        assert len(rows) == 17 and len({r['id'] for r in rows}) == 17
        extra = [r for r in rows if r['id'].startswith('startup19-')]
        assert len(extra) == 3
        jobs = [('clock', row, 1.0, 2**60) for row in rows] + [('nodes', row, 8.0, 250000) for row in extra]
        search = agent._search
        search.policy = None
        for mode, row, seconds, nodes in jobs:
            if any((Path.cwd() / flag).exists() for flag in ['STOP_TRAINING', 'STOP_BENCHMARK']):
                raise InterruptedError('User stop flag')
            board = chess.Board(row['start_fen'])
            for uci in row['history']:
                board.push_uci(uci)
            assert board.fen() == row['fen']
            stack = list(board.move_stack)
            for name in ['ttkey', 'ttcontext', 'ttdata', 'killers', 'history']:
                getattr(search, name).fill(0)
            tick = time.perf_counter()
            result = search.run(board, seconds, seconds, max_nodes=nodes, max_depth=64)
            elapsed = time.perf_counter() - tick
            assert result.move in board.legal_moves and board.fen() == row['fen'] and board.move_stack == stack
            report['results'].append(dict(id=row['id'], mode=mode, uci=result.move.uci(),
                depth=result.depth, score=result.score, nodes=result.nodes, seconds=result.elapsed,
                wall_seconds=elapsed, requested_seconds=seconds, requested_nodes=nodes,
                node_limit_reached=mode == 'nodes' and result.nodes >= nodes,
                repeats_large_error=result.move.uci() == row['played']))
            save_json(args.out, report)
            assert result.depth >= 1 and elapsed <= seconds + .25, 'Operational probe bound failed'
        report['status'] = 'complete'
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(args.out, report)
    print(json.dumps(dict(status=report['status'], init_seconds=report['init_seconds'], positions=len(report['results']))), flush=True)


if __name__ == '__main__':
    main()
