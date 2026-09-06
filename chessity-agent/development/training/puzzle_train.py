"""Supervised legal-masked soft puzzle targets with broad replay and a matched control."""

import os

for variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
    os.environ[variable] = "1"

import argparse
import json
import time
from collections import Counter
from pathlib import Path

import chess
import numpy as np

from engine.player_policy import SIZE, PlayerPolicy, encode_moves
from nn.model import Network
from nn.optim import Adam
from scripts.alien_rating_ladder import save_json, sha256
from training.puzzle_data import digest
from training.train import checkpoint


def masked_target_loss(logits, mask, targets):
    """Targets sum to one over legal moves; objectives never enter the game-value head."""
    if not np.allclose(targets.sum(axis=1), 1) or np.any(targets[~mask] != 0):
        raise ValueError("Invalid legal target distribution")
    if np.any(targets < 0) or not mask.any(axis=1).all():
        raise ValueError("Invalid probabilities or empty legal move set")
    scores = np.where(mask, logits, -1e9)
    scores -= scores.max(axis=1, keepdims=True)
    probs = np.exp(scores)
    probs /= probs.sum(axis=1, keepdims=True)
    loss = -np.sum(targets * np.log(np.maximum(probs, 1e-30))) / len(logits)
    return float(loss), (probs - targets) / len(logits)


def encode_rows(rows):
    encoded = []
    for row in rows:
        board = chess.Board(row.get("solver_fen", row.get("fen")))
        moves = list(board.legal_moves)
        if "target_distribution" in row:
            target = np.array([row["target_distribution"][m.uci()] for m in moves], dtype=np.float32)
        else:
            target = np.array([float(m.uci() == row["played_uci"]) for m in moves], dtype=np.float32)
        assert np.isclose(target.sum(), 1)
        encoded.append((encode_moves(board, moves).astype(np.float16), target))
    return encoded


def batch(encoded, indices):
    maximum = max(len(encoded[i][1]) for i in indices)
    x = np.zeros((len(indices), maximum, SIZE), dtype=np.float32)
    mask = np.zeros((len(indices), maximum), dtype=bool)
    target = np.zeros_like(mask, dtype=np.float32)
    for j, i in enumerate(indices):
        features, probabilities = encoded[i]
        count = len(probabilities)
        x[j, :count], mask[j, :count], target[j, :count] = features, True, probabilities
    return x, mask, target


def evaluate(net, encoded, indices):
    loss, correct, count = 0, 0, 0
    for start in range(0, len(indices), 32):
        ids = indices[start:start + 32]
        x, mask, target = batch(encoded, ids)
        logits = net.forward(x.reshape(-1, SIZE)).reshape(mask.shape)
        value, _ = masked_target_loss(logits, mask, target)
        loss += len(ids) * value
        choices = np.where(mask, logits, -1e9).argmax(axis=1)
        correct += int((target[np.arange(len(ids)), choices] == target.max(axis=1)).sum())
        count += len(ids)
    return {"cross_entropy": loss / count, "target_mode_agreement": correct / count, "positions": count}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("Fresh training output required")
    args.out.mkdir(parents=True)
    config = json.loads(Path("configs/puzzle-pilot.json").read_text())
    puzzles = [json.loads(line) for line in (args.data / "verified.jsonl").read_text().splitlines()]
    # Test rows are deliberately not encoded, inspected for accuracy, or used for replay here.
    puzzles = [r for r in puzzles if r["split"] != "test"]
    ordinary = [json.loads(line) for line in Path("runs/carlsen-curriculum-20260906/data/curriculum.jsonl").read_text().splitlines()]
    broad_train = sorted([r for r in ordinary if r["split"] == "train"], key=lambda r: digest(str(config["seed"]) + r["fen"]))[:1024]
    broad_validation = sorted([r for r in ordinary if r["split"] == "validation"], key=lambda r: digest(r["fen"]))[:128]
    rows = broad_train + broad_validation + puzzles
    encoded = encode_rows(rows)
    broad_ids = np.arange(len(broad_train))
    broad_valid = np.arange(len(broad_train), len(broad_train) + len(broad_validation))
    start = len(broad_train) + len(broad_validation)
    puzzle_train = np.array([i + start for i, r in enumerate(puzzles) if r["split"] == "train"])
    puzzle_valid = np.array([i + start for i, r in enumerate(puzzles) if r["split"] == "validation"])
    assert len(puzzle_train) >= 150 and len(puzzle_valid) >= 10
    baseline = PlayerPolicy(config["initial_policy"])
    failures = []
    for i in puzzle_train:
        board = chess.Board(rows[i]["solver_fen"])
        moves = list(board.legal_moves)
        chosen = moves[int(np.argmax(baseline.logits(board, moves)))].uci()
        if chosen not in rows[i]["acceptable_first_moves"]:
            failures.append(int(i))
    if not failures:
        raise ValueError("No verified training failures available for declared replay mix")
    save_json(args.out / "replay.json", {
        "student_sha256": sha256(config["initial_policy"]),
        "training_failure_ids": [rows[i]["id"] for i in failures],
        "cause": "Raw-policy disagreement with verified alternatives; underlying cause not inferred.",
        "test_or_validation_failures_used": 0,
        "objective": "Supervised move target only. No RL episode reward or game-value modification.",
    })
    config.update(data_sha256=sha256(args.data / "verified.jsonl"),
                  initial_policy_sha256=sha256(config["initial_policy"]),
                  broad_source_sha256=sha256("runs/carlsen-curriculum-20260906/data/curriculum.jsonl"))
    save_json(args.out / "config.json", config)
    report = {"config": config, "recipes": {}, "baseline": {},
              "scope": "Same architecture, initial weights, epochs, optimizer updates and batch size. Full-legal soft puzzle targets; ordinary human moves remain imitation labels. Legal move counts differ, so arithmetic FLOPs and wall time are measured, not asserted identical."}
    initial = Network.load(config["initial_policy"])
    report["baseline"] = {"broad": evaluate(initial, encoded, broad_valid),
                          "puzzle": evaluate(initial, encoded, puzzle_valid)}
    for recipe in ["control", "puzzle"]:
        net = Network.load(config["initial_policy"])
        optimizer = Adam(net.parameters(), lr=config["learning_rate"])
        rng = np.random.default_rng(config["seed"])
        out = args.out / recipe
        out.mkdir()
        best, logs, orders = float("inf"), [], []
        started = time.perf_counter()
        for epoch in range(config["epochs"]):
            if recipe == "control":
                indices = rng.permutation(broad_ids)
            else:
                # Sampling is bounded: each puzzle/failure can appear at most four times in an epoch.
                exposure, family_exposure = Counter(), Counter()

                def bounded_sample(pool, count):
                    chosen = []
                    for _ in range(4):
                        for i in rng.permutation(pool):
                            group = rows[i]["family_id"]
                            if exposure[i] >= 4 or family_exposure[group] >= 24:
                                continue
                            chosen.append(int(i))
                            exposure[i] += 1
                            family_exposure[group] += 1
                            if len(chosen) == count:
                                return np.array(chosen)
                    raise ValueError("Insufficient diverse training failures for bounded replay")

                fresh = bounded_sample(puzzle_train, 256)
                replay = bounded_sample(failures, 154)
                assert max(np.bincount(np.concatenate([fresh, replay]))) <= 4
                indices = np.concatenate([rng.choice(broad_ids, 614, replace=False), fresh, replay])
                rng.shuffle(indices)
            assert len(indices) == 1024
            orders.append(indices.tolist())
            total, moves_encoded = 0.0, 0
            for offset in range(0, len(indices), config["batch_size"]):
                ids = indices[offset:offset + config["batch_size"]]
                x, mask, target = batch(encoded, ids)
                optimizer.zero_grad()
                logits = net.forward(x.reshape(-1, SIZE)).reshape(mask.shape)
                loss, gradient = masked_target_loss(logits, mask, target)
                if not np.isfinite(loss) or not np.isfinite(gradient).all():
                    raise ValueError("Non-finite pilot learning signal")
                net.backward(gradient.reshape(-1, 1))
                optimizer.step()
                moves_encoded += int(mask.sum())
                total += len(ids) * loss
            valid = {"broad": evaluate(net, encoded, broad_valid), "puzzle": evaluate(net, encoded, puzzle_valid)}
            selection = 0.6 * valid["broad"]["cross_entropy"] + 0.4 * valid["puzzle"]["cross_entropy"]
            if selection < best:
                best = selection
                net.save(out / "best.npz")
            checkpoint(out / "last.npz", net, optimizer, epoch + 1, rng)
            row = dict(epoch=epoch + 1, train_loss=total / len(indices), validation=valid,
                       selection_score=selection, encoded_legal_moves=moves_encoded,
                       optimizer_steps=optimizer.t)
            logs.append(row)
            save_json(out / "metrics.json", logs)
            print(json.dumps({"recipe": recipe, **row}), flush=True)
        report["recipes"][recipe] = {"seconds": time.perf_counter() - started,
                                     "best_sha256": sha256(out / "best.npz"), "epochs": logs}
        save_json(out / "training-order.json", {"row_ids": [r.get("id", r.get("game_id", "")) for r in rows], "indices_by_epoch": orders})
    save_json(args.out / "report.json", report)


if __name__ == "__main__":
    main()
