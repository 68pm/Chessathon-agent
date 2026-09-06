"""Exact small chess counterexamples; diagnostic cases are never training labels."""

import os

for variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
    os.environ[variable] = "1"

import argparse
import json
import time
from pathlib import Path

import chess
import numpy as np

from engine.player_policy import PlayerPolicy
from engine.search import Search
from scripts.alien_rating_ladder import save_json

CASES = [
    (
        "opening_concrete_mate_over_development",
        "rnbqkbnr/pppp1ppp/8/4p3/6P1/5P2/PPPPP2P/RNBQKBNR b KQkq - 0 2",
        "mate_one",
    ),
    ("endgame_mate_over_king_improvement", "7k/8/5KQ1/8/8/8/8/8 w - - 0 1", "mate_one"),
    ("rook_promotion_avoids_queen_stalemate", "8/k1P5/2K5/8/8/8/8/8 w - - 0 1", "rook_promotion"),
    ("queenless_king_must_answer_check", "7k/8/8/8/8/8/7r/7K w - - 0 1", "legal_evasion"),
    ("stalemate_is_draw_not_pressure", "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1", "terminal_draw"),
    ("bare_kings_are_draw", "7k/8/6K1/8/8/8/8/8 w - - 0 1", "terminal_draw"),
    ("move_count_draw_not_king_activity", "7k/8/6K1/8/8/8/8/R7 w - - 100 1", "terminal_draw"),
]


def gold(board, kind):
    assert board.is_valid()
    if kind == "terminal_draw":
        assert board.outcome(claim_draw=True).winner is None
        return None
    legal = list(board.legal_moves)
    if kind == "legal_evasion":
        assert board.is_check()
        return set(legal)
    result = set()
    for move in legal:
        board.push(move)
        if kind == "mate_one" and board.is_checkmate():
            result.add(move)
        if kind == "rook_promotion" and not board.is_game_over():
            result.add(move)
        if kind == "rook_promotion" and move.promotion == chess.QUEEN:
            assert board.is_stalemate()
        board.pop()
    assert result
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--training", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    models = {
        "baseline": Path("candidates/classical-witty-magnus-v1/models/player-policy.npz"),
        "control": a.training / "control/best.npz",
        "curriculum": a.training / "curriculum/best.npz",
    }
    rows = []
    for model_name, path in models.items():
        for name, fen, kind in CASES:
            for mirror in [False, True]:
                board = chess.Board(fen)
                if mirror:
                    board = board.mirror()
                allowed = gold(board, kind)
                before = board.fen()
                result = Search(player_policy=PlayerPolicy(path), policy_cp=10).run(
                    board, seconds=2, max_depth=3
                )
                assert board.fen() == before
                passed = result.score == 0 if allowed is None else result.move in allowed
                rows.append(
                    {
                        "model": model_name,
                        "case": name,
                        "mirror": mirror,
                        "fen": before,
                        "expected_uci": None
                        if allowed is None
                        else sorted(m.uci() for m in allowed),
                        "chosen_uci": result.move.uci() if result.move else None,
                        "score": result.score,
                        "depth": result.depth,
                        "nodes": result.nodes,
                        "seconds": result.elapsed,
                        "passed": passed,
                    }
                )
    validation = [
        json.loads(line)
        for line in (a.training / "union.jsonl").read_text().splitlines()
        if json.loads(line)["split"] == "validation"
    ][:256]
    speed = {}
    for name, path in models.items():
        model = PlayerPolicy(path)
        durations = []
        for row in validation:
            board = chess.Board(row["fen"])
            moves = list(board.legal_moves)
            started = time.perf_counter()
            logits = model.logits(board, moves)
            durations.append((time.perf_counter() - started) * 1000)
            assert np.isfinite(logits).all()
        speed[name] = {
            "positions": len(durations),
            "median_ms": float(np.median(durations)),
            "p95_ms": float(np.percentile(durations, 95)),
            "max_ms": max(durations),
        }
    report = {
        "raw_policy_inference_timing": speed,
        "cases_per_model": 14,
        "results": rows,
        "passed_by_model": {
            name: sum(r["passed"] for r in rows if r["model"] == name) for name in models
        },
        "scope": "Independently enumerated mate-in-one, stalemate, underpromotion and draw-rule counterexamples, with colour mirrors. Known diagnostic positions, not an unseen chess-strength test. No opposition/fortress/tablebase mastery claim. In the underpromotion case a queen stalemates immediately; a rook retains mating material and avoids that draw. Existing root-policy endgame/check bypass remains in force.",
    }
    save_json(a.out, report)
    print(json.dumps(report["passed_by_model"]))


if __name__ == "__main__":
    main()
