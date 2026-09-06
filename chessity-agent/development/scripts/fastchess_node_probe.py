"""Isolated development-only node-limit instrumentation; does not modify an archived runtime."""

import argparse
import inspect
import json
import sys
import time
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--nodes", type=int, required=True)
    parser.add_argument("--clock-ms", type=int)
    parser.add_argument("--disable-opening", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(args.agent.resolve()))
    import chess

    import agent
    from engine.search import SearchTimeout, position_key

    Search = type(agent._search)

    if args.disable_opening:
        agent._opening = None

    rows = []
    for task in json.loads(args.tasks.read_text()):
        board = chess.Board(task["relevant_history"]["start_fen"])
        known = Counter({position_key(board): 1})
        for uci in task["relevant_history"]["moves"]:
            board.push_uci(uci)
            known[position_key(board)] += 1
        assert board.fen() == task["solver_fen"]
        options = dict(player_policy=agent._search.player_policy, policy_cp=agent._search.policy_cp) if hasattr(agent._search, "player_policy") else {}
        search = Search(agent._search.evaluate, style_tolerance=agent._search.style_tolerance, **options)
        original_tick = search.tick

        def tick():
            if search.nodes >= args.nodes:
                raise SearchTimeout
            original_tick()

        if args.clock_ms is None:
            search.tick = tick
        preferred = agent._opening(board) if getattr(agent, "_selective_opening", False) and agent._opening else None
        started = time.perf_counter()
        if args.clock_ms is None:
            options = dict(preferred_move=preferred, preference_cp=agent._config.get("alien_cp", 15)) if "preferred_move" in inspect.signature(search.run).parameters else {}
            result = search.run(board, seconds=30, soft=30, known=known, **options)
            rows.append(dict(id=task["id"], uci=result.move.uci(), nodes=result.nodes, depth=result.depth,
                             seconds=time.perf_counter() - started, score=result.score))
            assert result.nodes <= args.nodes
        else:
            agent._search = search
            agent._known.clear()
            agent._last = None
            uci = agent.get_move(board.fen(), args.clock_ms)
            rows.append(dict(id=task["id"], uci=uci, nodes=getattr(search, "nodes", 0),
                             seconds=time.perf_counter() - started, clock_ms=args.clock_ms,
                             includes_protocol_overhead=False))
        assert board.fen() == task["solver_fen"]
    args.out.write_text(json.dumps(rows, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
