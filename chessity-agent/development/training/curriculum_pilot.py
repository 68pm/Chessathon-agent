"""Equal-compute policy ablation: ordinary versus phase-balanced real examples."""

import os

for variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
    os.environ[variable] = "1"

import argparse
import json
import time
from pathlib import Path

import numpy as np

from engine.player_policy import SIZE, PlayerPolicy
from nn.model import Network
from nn.optim import Adam
from scripts.alien_rating_ladder import save_json, sha256
from training.chess_curriculum import PHASES
from training.player_policy import build, choice_loss, evaluate, full_legal_test
from training.train import checkpoint


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    config = json.loads(Path("configs/carlsen-curriculum-pilot.json").read_text())
    if a.out.exists():
        raise ValueError("Use a fresh pilot training path")
    a.out.mkdir(parents=True)
    groups = {
        recipe: [json.loads(line) for line in (a.data / f"{recipe}.jsonl").read_text().splitlines()]
        for recipe in config["recipes"]
    }
    union = {}
    for group in groups.values():
        for row in group:
            if row["fen"] in union:
                assert union[row["fen"]] == row
            union[row["fen"]] = row
    rows = [union[key] for key in sorted(union)]
    path = a.out / "union.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    cache = a.out / "cache"
    cache.mkdir()
    rows, features, mask, split = build(path, cache, config["seed"])
    assert not (split == 2).any()
    lookup = {row["fen"]: i for i, row in enumerate(rows)}
    validation = np.flatnonzero(split == 1)
    assert len(validation) == config["validation_positions_shared"]
    train_game_ids = {row["game_id"] for row in rows if row["split"] == "train"}
    validation_game_ids = {row["game_id"] for row in rows if row["split"] == "validation"}
    assert not train_game_ids & validation_game_ids
    # Verify a real 1,024-position pipeline pilot before the two full recipe runs.
    pilot_ids = np.flatnonzero(split == 0)[:1024]
    pilot_net = Network.load(config["initial_policy"])
    pilot_optimizer = Adam(pilot_net.parameters(), lr=config["learning_rate"])
    before = evaluate(pilot_net, features, mask, pilot_ids)
    for offset in range(0, len(pilot_ids), 128):
        ids = pilot_ids[offset : offset + 128]
        x = np.asarray(features[ids], dtype=np.float32)
        assert np.isfinite(x).all() and mask[ids, 0].all()
        pilot_optimizer.zero_grad()
        logits = pilot_net.forward(x.reshape(-1, SIZE)).reshape(len(ids), 5)
        loss, gradient = choice_loss(logits, mask[ids])
        assert np.isfinite(loss) and np.isfinite(gradient).all()
        pilot_net.backward(gradient.reshape(-1, 1))
        pilot_optimizer.step()
    after = evaluate(pilot_net, features, mask, pilot_ids)
    save_json(
        a.out / "pipeline-pilot.json",
        {
            "verified_positions": len(pilot_ids),
            "input_features": SIZE,
            "before": before,
            "after": after,
            "finite_features_loss_gradients": True,
            "whole_game_split_overlap": 0,
            "purpose": "Discarded sanity-check model, not selected or used to initialise either comparison recipe.",
        },
    )
    report = {
        "config": config,
        "initial_policy_sha256": sha256(config["initial_policy"]),
        "union_sha256": sha256(path),
        "recipes": {},
        "scope": "Shared encoded features and negative alternatives for overlapping positions. Same validation examples, seed, initial weights, optimizer, batch count and epochs. Checkpoint selection uses validation only; no final-test data inspected.",
    }
    baseline = Network.load(config["initial_policy"])
    report["baseline_validation"] = evaluate(baseline, features, mask, validation)
    for recipe in config["recipes"]:
        started = time.perf_counter()
        target = a.out / recipe
        target.mkdir()
        net = Network.load(config["initial_policy"])
        optimizer = Adam(net.parameters(), lr=config["learning_rate"])
        rng = np.random.default_rng(config["seed"])
        train = np.array([lookup[row["fen"]] for row in groups[recipe] if row["split"] == "train"])
        assert len(train) == config["train_positions_per_recipe"]
        best, logs = float("inf"), []
        for epoch in range(config["epochs"]):
            tick = time.perf_counter()
            indices = rng.permutation(train)
            total = 0.0
            for offset in range(0, len(indices), config["batch_size"]):
                ids = indices[offset : offset + config["batch_size"]]
                x = np.asarray(features[ids], dtype=np.float32)
                optimizer.zero_grad()
                logits = net.forward(x.reshape(-1, SIZE)).reshape(len(ids), 5)
                loss, gradient = choice_loss(logits, mask[ids])
                net.backward(gradient.reshape(-1, 1))
                optimizer.step()
                total += loss * len(ids)
            valid = evaluate(net, features, mask, validation)
            assert np.isfinite(valid["cross_entropy"])
            entry = {
                "epoch": epoch + 1,
                "train_loss": total / len(train),
                "validation": valid,
                "seconds": time.perf_counter() - tick,
            }
            logs.append(entry)
            if valid["cross_entropy"] < best:
                best = valid["cross_entropy"]
                net.save(target / "best.npz")
            checkpoint(target / "last.npz", net, optimizer, epoch + 1, rng)
            print(recipe + ": " + json.dumps(entry), flush=True)
        report["recipes"][recipe] = {
            "epochs": logs,
            "train_positions": len(train),
            "seconds": time.perf_counter() - started,
            "best_sha256": sha256(target / "best.npz"),
        }
    report["phase_validation"] = {}
    for name, model_path in [
        ("baseline", Path(config["initial_policy"])),
        ("control", a.out / "control/best.npz"),
        ("curriculum", a.out / "curriculum/best.npz"),
    ]:
        net, model = Network.load(model_path), PlayerPolicy(model_path)
        result = {}
        for stage in PHASES:
            ids = np.array([i for i in validation if rows[i]["primary_phase"] == stage])
            if len(ids):
                result[stage] = {
                    "sampled_choices": evaluate(net, features, mask, ids),
                    "full_legal": full_legal_test(model, rows, ids, config["seed"], count=1024),
                }
        report["phase_validation"][name] = result
    save_json(a.out / "report.json", report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
