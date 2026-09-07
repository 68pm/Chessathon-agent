"""Isolated critical-position probe with reconstructed game history."""

import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--seconds', type=float, default=1.0)
    parser.add_argument('--nodes', type=int)
    args = parser.parse_args()
    sys.path.insert(0, str(args.candidate.resolve()))
    import chess

    import agent

    rows = [json.loads(line) for line in args.audit.read_text().splitlines()]
    rows = [row for row in rows if row['label'] == 'verified_200cp_error']
    results = []
    for row in rows:
        board = chess.Board(row['start_fen'])
        for uci in row['history']:
            board.push_uci(uci)
        assert board.fen() == row['fen']
        if hasattr(agent._search, 'ttkey'):
            agent._search.policy = None
            agent._search.ttkey.fill(0)
            agent._search.ttcontext.fill(0)
            agent._search.killers.fill(0)
            agent._search.history.fill(0)
            result = agent._search.run(board, args.seconds, args.seconds,
                                       max_nodes=args.nodes or 2**60)
        else:
            from collections import Counter

            from engine.search import Search, position_key

            search = Search(agent._search.evaluate)
            replay = board.root()
            counts = Counter([position_key(replay)])
            for move in board.move_stack:
                replay.push(move)
                counts[position_key(replay)] += 1
            result = search.run(board, args.seconds, args.seconds, known=counts)
        assert result.move in board.legal_moves
        assert board.fen() == row['fen']
        results.append(dict(id=row['id'], fen=board.fen(), original_move=row['played'],
                            uci=result.move.uci(), depth=result.depth, nodes=result.nodes,
                            seconds=result.elapsed, score=result.score,
                            agrees_with_deep_teacher=result.move.uci() == row['verification'][-1]['best']['pv'][0],
                            repeats_large_error=result.move.uci() == row['played']))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(dict(candidate=str(args.candidate), requested_seconds=args.seconds,
        results=results, scope='Previously audited development positions. Teacher top-one agreement is diagnostic, not a new strength claim. Root policy preference disabled in both probes.'), indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(positions=len(results), teacher_agreement=sum(r['agrees_with_deep_teacher'] for r in results),
                         repeats_error=sum(r['repeats_large_error'] for r in results),
                         nodes=sum(r['nodes'] for r in results), seconds=sum(r['seconds'] for r in results))))


if __name__ == '__main__':
    main()
