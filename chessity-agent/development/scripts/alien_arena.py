"""Small opening-specific ablation. This is not the general-rating test suite."""

import json
from pathlib import Path

import chess

from engine.openings import ALIEN_LINE
from harness.referee import FAILED_TERMINATIONS, play_match
from harness.sandbox import local


def main():
    board = chess.Board()
    for san in ALIEN_LINE[:10]:
        board.push_san(san)
    candidates = [
        Path("runs/unattended-20260905-away/candidate-300000-hybrid"),
        Path("candidates/alien-300k-hybrid-v2"),
    ]
    opponents = [
        Path("baselines/greedy"),
        Path("baselines/minimax"),
        Path("champions/classical-v2"),
    ]
    rows = []
    out = Path("runs/alien-opening-arena.json")
    for opponent in opponents:
        for candidate in candidates:
            result = play_match(
                local(candidate), local(opponent), 6000, 100, ply_cap=300, start_fen=board.fen()
            )
            row = {
                "candidate": candidate.name,
                "opponent": opponent.name,
                "candidate_white": True,
                "result": result.result,
                "score": {"white": 1, "draw": 0.5, "black": 0}.get(result.result),
                "termination": result.termination,
                "pgn": result.pgn,
            }
            rows.append(row)
            out.write_text(
                json.dumps(
                    {
                        "purpose": "Opening-specific smoke ablation, both candidates White from the same pre-sacrifice FEN. Three heterogeneous unrated opponents, one game each: no strength or style-effect estimate.",
                        "base_ms": 6000,
                        "increment_ms": 100,
                        "start_fen": board.fen(),
                        "games": rows,
                    },
                    indent=2,
                )
            )
            print(
                f"{candidate.name} vs {opponent.name}: {row['score']} {row['termination']}",
                flush=True,
            )
            if result.termination in FAILED_TERMINATIONS or result.result == "void":
                raise RuntimeError("Reliability failure in opening arena")


if __name__ == "__main__":
    main()
