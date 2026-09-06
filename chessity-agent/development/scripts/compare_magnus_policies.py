"""Compare both move policies on identical held-out positions from both players."""

import os

for variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
    os.environ[variable] = "1"

import json
from pathlib import Path

import numpy as np

from engine.player_policy import PlayerPolicy
from scripts.alien_rating_ladder import save_json, sha256
from training.player_policy import full_legal_test


def main():
    run = Path("runs/magnus-mixed-20260906")
    rows = [json.loads(line) for line in (run / "mixture/samples.jsonl").read_text().splitlines()]
    report = {"samples_sha256": sha256(run / "mixture/samples.jsonl"), "models": {}}
    for name, path in [
        ("previous_witty", Path("candidates/mixed-classical-witty-v1/models/player-policy.npz")),
        ("magnus_witty", run / "policy/best.npz"),
    ]:
        model = PlayerPolicy(path)
        result = {"sha256": sha256(path)}
        for player in ["magnuscarlsen", "witty_alien"]:
            indices = np.array(
                [
                    i
                    for i, row in enumerate(rows)
                    if row["split"] == "test" and row["player"] == player
                ]
            )
            result[player] = full_legal_test(model, rows, indices, 20260906, count=1000)
        report["models"][name] = result
    save_json(run / "policy-comparison.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
