"""Paired official-process matches, with game-level uncertainty and complete PGNs."""

import argparse
import json
import math
from pathlib import Path

import chess

from harness.referee import FAILED_TERMINATIONS, play_match
from harness.sandbox import local

OPENINGS = [
    [],
    ["e2e4", "e7e5", "g1f3", "b8c6"],
    ["d2d4", "d7d5", "c2c4", "e7e6"],
    ["e2e4", "c7c5", "g1f3", "d7d6"],
    ["d2d4", "g8f6", "c2c4", "e7e6"],
    ["c2c4", "e7e5", "b1c3", "g8f6"],
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--agent", type=Path, default=Path("."))
    p.add_argument("--opponent", type=Path, default=Path("baselines/minimax"))
    p.add_argument("--games", type=int, default=12)
    p.add_argument("--base-ms", type=int, default=3000)
    p.add_argument("--increment-ms", type=int, default=50)
    p.add_argument("--ply-cap", type=int, default=300)
    p.add_argument("--out", type=Path, default=Path("runs/arena.json"))
    a = p.parse_args()
    if a.games < 2 or a.games % 2:
        p.error("Use a positive even game count for colour pairs")
    rows, scores = [], []
    a.out.parent.mkdir(parents=True, exist_ok=True)
    for i in range(a.games):
        b = chess.Board()
        for uci in OPENINGS[(i // 2) % len(OPENINGS)]:
            b.push_uci(uci)
        white = i % 2 == 0
        first, second = (a.agent, a.opponent) if white else (a.opponent, a.agent)
        outcome = play_match(
            local(first),
            local(second),
            a.base_ms,
            a.increment_ms,
            ply_cap=a.ply_cap,
            start_fen=b.fen(),
        )
        score = (
            0.5
            if outcome.result == "draw"
            else float(outcome.result == ("white" if white else "black"))
        )
        scores.append(score)
        rows.append(
            {
                "game": i + 1,
                "candidate_white": white,
                "fen": b.fen(),
                "score": score,
                "termination": outcome.termination,
                "pgn": outcome.pgn,
            }
        )
        print(f"{i + 1}/{a.games}: {score} {outcome.termination}", flush=True)
        a.out.write_text(json.dumps({"games": rows}, indent=2))
        if outcome.termination in FAILED_TERMINATIONS or outcome.result == "void":
            raise RuntimeError(f"Reliability failure: {outcome.termination}; see {a.out}")
    mean = sum(scores) / len(scores)
    # Pair is the sampling unit. Normal approximation is only descriptive for small n.
    pairs = [(scores[i] + scores[i + 1]) / 2 for i in range(0, len(scores), 2)]
    se = (
        math.sqrt(sum((s - mean) ** 2 for s in pairs) / (len(pairs) - 1) / len(pairs))
        if len(pairs) > 1
        else None
    )
    summary = {
        "wins": scores.count(1),
        "draws": scores.count(0.5),
        "losses": scores.count(0),
        "score": mean,
        "pair_standard_error": se,
        "games": rows,
        "base_ms": a.base_ms,
        "increment_ms": a.increment_ms,
        "ply_cap": a.ply_cap,
        "agent": str(a.agent),
        "opponent": str(a.opponent),
        "caution": "Small paired sample; no Elo claim. Local CPU is not the server CPU.",
    }
    a.out.write_text(json.dumps(summary, indent=2))
    print(json.dumps({k: v for k, v in summary.items() if k != "games"}), flush=True)


if __name__ == "__main__":
    main()
