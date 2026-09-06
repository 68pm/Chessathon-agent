import argparse
import json
import random
import time
from pathlib import Path

import chess
import numpy as np

import agent
from engine.search import Search


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--calls", type=int, default=10000)
    p.add_argument("--games", type=int, default=200)
    a = p.parse_args()
    rng, b = random.Random(20260905), chess.Board()
    timings, unique = [], set()
    for i in range(a.calls):
        if b.is_game_over(claim_draw=True) or b.ply() >= 250:
            b.reset()
        fen = b.fen()
        unique.add(fen)
        start = time.monotonic()
        # 10% exercise search; 90% exercise emergency fallback.
        move = chess.Move.from_uci(agent.get_move(fen, 60 if i % 10 == 0 else 15))
        timings.append((time.monotonic() - start) * 1000)
        assert move in b.legal_moves, fen
        b.push(rng.choice(list(b.legal_moves)))
    completed = capped = total_plies = 0
    for game in range(a.games):
        b, search = chess.Board(), Search()
        for ply in range(120):
            if b.is_game_over(claim_draw=True):
                completed += 1
                break
            if b.turn == bool(game % 2):
                move = search.run(b, 0.001).move
            else:
                legal = list(b.legal_moves)
                if game % 2:
                    legal.sort(key=lambda m: bool(b.is_capture(m)), reverse=True)
                    move = legal[0]
                else:
                    move = rng.choice(legal)
            assert move in b.legal_moves
            b.push(move)
            total_plies += 1
        else:
            capped += 1
    result = {
        "calls": a.calls,
        "unique_fens": len(unique),
        "search_calls": (a.calls + 9) // 10,
        "p95_ms": float(np.percentile(timings, 95)),
        "max_ms": max(timings),
        "short_games": a.games,
        "completed": completed,
        "ply_capped": capped,
        "plies": total_plies,
        "illegal_moves": 0,
        "crashes": 0,
        "note": "Stress games at 1ms search, not a strength measurement or real-clock test.",
    }
    Path("runs").mkdir(exist_ok=True)
    Path("runs/reliability.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
