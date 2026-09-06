"""Collect our own games and prioritised disagreement positions for later offline labels."""

import argparse
import json
import random
from pathlib import Path

import chess

from engine.evaluation import Evaluator
from engine.neural import NeuralValue
from engine.search import Search
from scripts.arena_compare import OPENINGS


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--games", type=int, default=20)
    p.add_argument("--seconds", type=float, default=0.02)
    p.add_argument("--out", type=Path, default=Path("data/selfplay.jsonl"))
    p.add_argument("--seed", type=int, default=20260905)
    a = p.parse_args()
    rng = random.Random(a.seed)
    model = NeuralValue("models/value.npz")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    existing_games = set()
    if a.out.exists():
        existing_games = {
            json.loads(line)["game"] for line in a.out.read_text().splitlines() if line
        }
    for game in range(a.games):
        # Consume deterministic opening selection even when resuming.
        opening = rng.choice(OPENINGS)
        if game in existing_games:
            continue
        b, samples = chess.Board(), []
        for move in opening:
            b.push_uci(move)
        champion, candidate = Search(), Search(Evaluator("hybrid", model))
        for ply in range(200):
            if b.is_game_over(claim_draw=True):
                break
            original = champion.run(b, a.seconds)
            challenger = candidate.run(b, a.seconds)
            if original.move != challenger.move or abs(original.score - challenger.score) > 120:
                samples.append(
                    {
                        "fen": b.fen(),
                        "champion_move": original.move.uci(),
                        "candidate_move": challenger.move.uci(),
                        "cp": original.score,
                        "depth": original.depth,
                        "group": f"selfplay-{a.seed}-{game}",
                        "game": game,
                        "label_warning": "Own shallow search score, not a strong external teacher label",
                    }
                )
            chosen = original if b.turn == bool(game % 2) else challenger
            b.push(chosen.move)
        with a.out.open("a") as output:
            for row in samples:
                row["result"] = b.result(claim_draw=True)
                output.write(json.dumps(row) + "\n")
        print(
            f"game {game}: {b.result(claim_draw=True)}, {len(samples)} replay samples", flush=True
        )


if __name__ == "__main__":
    main()
