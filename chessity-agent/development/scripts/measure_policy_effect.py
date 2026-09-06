"""Compare learned preferences at equal completed depth on held-out positions."""

import os

for variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
    os.environ[variable] = "1"

import argparse
import hashlib
import json
import random
from collections import Counter
from pathlib import Path

import chess

from engine.evaluation import Evaluator, classical, phase, style_score
from engine.neural import NeuralValue
from engine.player_policy import PlayerPolicy
from engine.search import Search


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    policy = PlayerPolicy(args.candidate / "models/player-policy.npz")
    evaluator = Evaluator("hybrid", NeuralValue(args.candidate / "models/value.npz"))
    rows = [json.loads(line) for line in args.samples.read_text().splitlines()]
    rows = [row for row in rows if row["split"] == "test"]
    random.Random(20260906).shuffle(rows)
    pairs, skipped, candidates = [], 0, 0
    totals = {"baseline": Counter(), "learned_policy": Counter()}
    for row in rows:
        board = chess.Board(row["fen"])
        if (
            board.is_check()
            or abs(classical(board)) >= 300
            or phase(board) <= 0.20
            or board.is_game_over()
        ):
            continue
        candidates += 1
        pair = {"fen": row["fen"], "observed_move": row["played_uci"]}
        for name in (
            ["baseline", "learned_policy"] if candidates % 2 else ["learned_policy", "baseline"]
        ):
            search = Search(evaluator, player_policy=policy if name == "learned_policy" else None)
            result = search.run(board, 2.0, max_depth=2)
            pair[name] = {
                "move": result.move.uci(),
                "depth": result.depth,
                "check": board.gives_check(result.move),
                "capture": board.is_capture(result.move),
                "style_score": style_score(board, result.move),
                "nodes": result.nodes,
            }
        if any(pair[name]["depth"] != 2 for name in totals):
            skipped += 1
        else:
            pairs.append(pair)
            for name in totals:
                totals[name]["checks"] += int(pair[name]["check"])
                totals[name]["captures"] += int(pair[name]["capture"])
                totals[name]["style_score_sum"] += pair[name]["style_score"]
                totals[name]["observed_move_matches"] += int(
                    pair[name]["move"] == row["played_uci"]
                )
        if len(pairs) >= 64 or candidates >= 96:
            break
    report = {
        "completed_pairs": len(pairs),
        "incomplete_depth_pairs_skipped": skipped,
        "changed_moves": sum(r["baseline"]["move"] != r["learned_policy"]["move"] for r in pairs),
        "totals": totals,
        "pairs": pairs,
        "sample_sha256": hashlib.sha256(args.samples.read_bytes()).hexdigest(),
        "protocol": "First 64 completed depth-two pairs from a fixed-seed shuffle of eligible test positions, max 96 attempts. Same hybrid evaluator; repertoire disabled; only learned root preferences differ. Search order alternates. No parameter changes based on this test.",
        "limitation": "Small, forcing-biased held-out position sample and shallow completed depth. Changes in checking/capturing frequency do not establish attacking quality, stronger play or a stable style change.",
    }
    args.out.write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "pairs"}, indent=2))


if __name__ == "__main__":
    main()
