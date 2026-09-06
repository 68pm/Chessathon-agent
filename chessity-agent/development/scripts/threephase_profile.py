"""Profile only diagnostic-training positions in an isolated frozen baseline import."""

import argparse
import cProfile
import json
import pstats
import sys
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(args.agent.resolve()))
    import chess

    import agent
    from engine.search import SearchTimeout, position_key

    rows = json.loads(args.tasks.read_text())
    tasks = []
    for phase in ["opening", "middlegame", "transition", "endgame"]:
        tasks.extend([r for r in rows if r["primary_phase"] == phase][:2])
    assert len(tasks) == 8 and all(row["split"] == "train" for row in tasks)
    profile, results = cProfile.Profile(), []
    for row in tasks:
        board = chess.Board(row["relevant_history"]["start_fen"])
        known = Counter({position_key(board): 1})
        for uci in row["relevant_history"]["moves"]:
            board.push_uci(uci)
            known[position_key(board)] += 1
        assert board.fen() == row["solver_fen"]
        search = type(agent._search)(agent._search.evaluate, player_policy=agent._search.player_policy,
                                     policy_cp=agent._search.policy_cp)
        original_tick = search.tick

        def tick():
            if search.nodes >= 2000:
                raise SearchTimeout
            original_tick()

        search.tick = tick
        result = profile.runcall(search.run, board, seconds=30, soft=30, known=known)
        assert board.fen() == row["solver_fen"] and result.move in board.legal_moves
        results.append(dict(id=row["id"], phase=row["primary_phase"], nodes=result.nodes,
                            completed_depth=result.depth, uci=result.move.uci(), profiled_seconds=result.elapsed))
    stats = pstats.Stats(profile)
    functions = [dict(file=file, line=line, function=function, primitive_calls=value[0], calls=value[1],
                      self_seconds=value[2], cumulative_seconds=value[3])
                 for (file, line, function), value in stats.stats.items()]
    report = dict(agent=str(args.agent), training_positions=results,
                  functions=sorted(functions, key=lambda item: item["cumulative_seconds"], reverse=True)[:35],
                  total_profiled_seconds=stats.total_tt,
                  scope="Diagnostic training positions only. Profiling adds overhead; these times are for cost attribution, not a production-speed claim.")
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"positions": len(results), "depths": [r["completed_depth"] for r in results],
                      "costs": [{k: r[k] for k in ["function", "calls", "self_seconds", "cumulative_seconds"]}
                                for r in report["functions"][:16]]}, indent=2))


if __name__ == "__main__":
    main()
