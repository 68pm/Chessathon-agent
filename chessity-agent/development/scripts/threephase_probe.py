"""Isolated saved-runtime probes with reconstructed history; never fits weights."""

import argparse
import json
import sys
import time
from collections import Counter
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", type=Path, required=True)
    parser.add_argument("--tasks", type=Path, required=True)
    parser.add_argument("--nodes", type=int)
    parser.add_argument("--clock-ms", type=int)
    parser.add_argument("--disable-opening", action="store_true")
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    assert (args.nodes is None) != (args.clock_ms is None)
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(args.agent.resolve()))
    import chess

    import agent
    from engine.search import SearchTimeout, position_key

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
        search = type(agent._search)(agent._search.evaluate, style_tolerance=agent._search.style_tolerance,
                                     player_policy=agent._search.player_policy, policy_cp=agent._search.policy_cp)
        if hasattr(agent._search, "selective"):
            search.selective = agent._search.selective
        original_tick = search.tick

        def tick():
            if search.nodes >= args.nodes:
                raise SearchTimeout
            original_tick()

        preferred = agent._opening(board) if getattr(agent, "_selective_opening", False) and agent._opening else None
        started = time.perf_counter()
        if args.nodes is not None:
            search.tick = tick
            result = search.run(board, seconds=30, soft=30, known=known, preferred_move=preferred,
                                preference_cp=agent._config.get("alien_cp", 15))
            uci, depth, score = result.move.uci(), result.depth, result.score
            assert result.nodes <= args.nodes
        else:
            agent._search = search
            agent._last = None
            agent._known = known.copy()
            # get_move records the current observed root itself.
            agent._known[position_key(board)] -= 1
            uci = agent.get_move(board.fen(), args.clock_ms)
            depth, score = None, None
        rows.append(dict(id=task["id"], uci=uci, nodes=search.nodes, depth=depth, score=score,
                         seconds=time.perf_counter() - started, clock_ms=args.clock_ms,
                         search_class=f"{type(search).__module__}.{type(search).__name__}",
                         scout_searches=getattr(search, "scout_searches", None),
                         full_researches=getattr(search, "full_researches", None),
                         reductions=getattr(search, "reductions", None)))
        assert board.fen() == task["solver_fen"] and chess.Move.from_uci(uci) in board.legal_moves
    args.out.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
