"""Bounded full-window diagnosis of known mistakes, not a strength test."""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import chess
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--targets', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--id', required=True)
    parser.add_argument('--min-depth', type=int, default=1)
    parser.add_argument('--max-depth', type=int, default=6)
    parser.add_argument('--seconds', type=float, default=3)
    parser.add_argument('--nodes', type=int, default=1_000_000)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('Keep prior diagnostic results.')
    sys.path.insert(0, str(args.candidate.resolve()))
    from engine.compiled_driver import arrays, core, decode

    import agent

    search = agent._search
    search.policy = None
    row = next(r for r in map(json.loads, args.targets.read_text().splitlines()) if r['id'] == args.id)
    position = chess.Board(row['start_fen'])
    for uci in row['history']:
        position.push_uci(uci)
    assert position.fen() == row['fen']

    def clear():
        for a in (search.ttkey, search.ttcontext, search.ttdata, search.killers, search.history):
            a.fill(0)

    records = []
    for depth in range(args.min_depth, args.max_depth + 1):
        clear()
        result = search.run(position, args.seconds, args.seconds, max_depth=depth, max_nodes=args.nodes)
        record = dict(depth=depth, root=dict(uci=result.move.uci(), score=result.score,
                      completed_depth=result.depth, nodes=result.nodes), choices=[])
        for uci in dict.fromkeys([row['played'], row['verification'][-1]['best']['pv'][0]]):
            child = position.copy(stack=True)
            child.push_uci(uci)
            board, state = arrays(child)
            saved, ss = board.copy(), state.copy()
            hashes = np.zeros(800, dtype=np.uint64)
            replay, past = child.copy(stack=True), []
            for _ in range(min(child.halfmove_clock, len(child.move_stack)) + 1):
                b, s = arrays(replay)
                past.append(core.position_hash(b, s))
                if not replay.move_stack:
                    break
                replay.pop()
            past.reverse()
            hashes[:len(past)] = past
            context = np.uint64(sum(map(int, past)) & ((1 << 64) - 1))
            clear()
            control = np.array([0, 0, args.nodes], dtype=np.int64)
            started = time.perf_counter()
            value = -core.search(board, state, depth - 1, -31000, 31000, 1, 0,
                hashes, len(past), context, search.ttkey, search.ttcontext, search.ttdata,
                search.killers, search.history, control, started + args.seconds,
                search.weights, search.bias, search.output, search.blend, search.conversion,
                search.reductions, core.build_accumulator(board, search.weights, search.bias))
            assert np.array_equal(board, saved) and np.array_equal(state, ss)
            slot = int(past[-1]) & (len(search.ttkey) - 1)
            reply = int(search.ttdata[slot, 3])
            record['choices'].append(dict(uci=uci, score=int(value), complete=not bool(control[1]),
                nodes=int(control[0]), seconds=time.perf_counter() - started,
                static=-int(core.classical(board, state, search.conversion)),
                reply=decode(reply).uci() if reply else None))
        records.append(record)
        print(json.dumps(record), flush=True)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(dict(id=args.id, fen=row['fen'], candidate=str(args.candidate),
        source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        core_sha256=hashlib.sha256(Path(core.__file__).read_bytes()).hexdigest(),
        limits=dict(seconds=args.seconds, nodes=args.nodes), records=records), indent=2) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()
