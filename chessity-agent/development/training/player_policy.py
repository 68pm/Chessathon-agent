"""Train a small original move-ranking network from authorised player decisions."""

import os

for variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
    os.environ[variable] = "1"

import argparse
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

import chess
import numpy as np

from engine.player_policy import SIZE, PlayerPolicy, encode_moves
from nn.model import Network
from nn.optim import Adam
from training.train import checkpoint


def choice_loss(logits, mask):
    scores = np.where(mask, logits, -1e9)
    scores -= scores.max(axis=1, keepdims=True)
    probs = np.exp(scores)
    probs /= probs.sum(axis=1, keepdims=True)
    loss = -np.log(np.maximum(probs[:, 0], 1e-30)).mean()
    gradient = probs.copy()
    gradient[:, 0] -= 1
    gradient /= len(scores)
    return float(loss), gradient


def build(samples, out, seed):
    rows = [json.loads(line) for line in samples.read_text(encoding="utf-8").splitlines()]
    if not rows:
        raise ValueError("No real player examples supplied")
    features = np.lib.format.open_memmap(
        out / "features.npy", mode="w+", dtype=np.float16, shape=(len(rows), 5, SIZE)
    )
    mask = np.zeros((len(rows), 5), dtype=bool)
    split = np.zeros(len(rows), dtype=np.uint8)
    rng = np.random.default_rng(seed)
    for i, row in enumerate(rows):
        board = chess.Board(row["fen"])
        target = chess.Move.from_uci(row["played_uci"])
        legal = list(board.legal_moves)
        if target not in legal:
            raise ValueError(f"Illegal target at row {i}")
        alternatives = [move for move in legal if move != target]
        rng.shuffle(alternatives)
        chosen = [target] + alternatives[:4]
        features[i, : len(chosen)] = encode_moves(board, chosen)
        features[i, len(chosen) :] = 0
        mask[i, : len(chosen)] = True
        split[i] = {"train": 0, "validation": 1, "test": 2}[row["split"]]
        if (i + 1) % 5000 == 0:
            features.flush()
            print(f"Encoded {i + 1}/{len(rows)} observed decisions", flush=True)
    features.flush()
    np.savez(out / "labels.npz", mask=mask, split=split)
    return rows, features, mask, split


def evaluate(net, features, mask, indices, batch_size=256):
    loss, correct = 0.0, 0
    for offset in range(0, len(indices), batch_size):
        ids = indices[offset : offset + batch_size]
        x = np.asarray(features[ids], dtype=np.float32)
        logits = net.forward(x.reshape(-1, SIZE)).reshape(len(ids), 5)
        value, _ = choice_loss(logits, mask[ids])
        loss += value * len(ids)
        correct += int((np.where(mask[ids], logits, -1e9).argmax(axis=1) == 0).sum())
    return {
        "cross_entropy": loss / len(indices),
        "top1": correct / len(indices),
        "positions": len(indices),
        "uniform_top1": float(np.mean(1 / mask[indices].sum(axis=1))),
    }


def full_legal_test(model, rows, test_indices, seed, count=1000):
    rng = np.random.default_rng(seed)
    indices = rng.choice(test_indices, min(count, len(test_indices)), replace=False)
    counts = Counter()
    chance = 0.0
    for i in indices:
        row = rows[i]
        board = chess.Board(row["fen"])
        moves = list(board.legal_moves)
        target = chess.Move.from_uci(row["played_uci"])
        order = np.argsort(-model.logits(board, moves), kind="stable")
        selected = moves[order[0]]
        counts["positions"] += 1
        counts["top1"] += int(selected == target)
        counts["top3"] += int(target in [moves[j] for j in order[:3]])
        counts["selected_checks"] += int(board.gives_check(selected))
        counts["observed_checks"] += int(row["gives_check"])
        counts["selected_captures"] += int(board.is_capture(selected))
        counts["observed_captures"] += int(row["is_capture"])
        chance += 1 / len(moves)
    return {
        "counts": dict(counts),
        "top1": counts["top1"] / len(indices),
        "top3": counts["top3"] / len(indices),
        "uniform_top1": chance / len(indices),
        "limitation": "Held-out whole games under the documented source sampling schemes. Imitation agreement is not tactical accuracy or Elo; exact FEN duplicates removed but related positions can remain.",
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--seed", type=int, default=20260906)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--initial-policy", type=Path)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument(
        "--runtime-context",
        default="Existing self-trained 300k evaluator retained without fabricated value labels",
    )
    args = parser.parse_args()
    config = {
        "samples_sha256": hashlib.sha256(args.samples.read_bytes()).hexdigest(),
        "seed": args.seed,
        "shape": [SIZE, 64, 32, 1],
        "negatives": 4,
        "objective": "Observed player move against up to four uniformly sampled other legal moves",
        "value_model": args.runtime_context,
    }
    if args.initial_policy:
        config["initial_policy_sha256"] = hashlib.sha256(
            args.initial_policy.read_bytes()
        ).hexdigest()
    if args.learning_rate != 0.001:
        config["learning_rate"] = args.learning_rate
    if not 0 < args.learning_rate <= 0.1:
        raise ValueError("Invalid learning rate")
    if args.out.exists() and not args.resume:
        raise ValueError("Use a new output folder, or --resume")
    args.out.mkdir(parents=True, exist_ok=True)
    if args.resume:
        if json.loads((args.out / "config.json").read_text()) != config:
            raise ValueError("Resume data/configuration mismatch")
        rows = [json.loads(line) for line in args.samples.read_text(encoding="utf-8").splitlines()]
        if (args.out / "features.npy").exists():
            features = np.load(args.out / "features.npy", mmap_mode="r")
            with np.load(args.out / "labels.npz", allow_pickle=False) as data:
                mask, split = data["mask"], data["split"]
        else:
            # Feature caches can be discarded after fitting; recover them deterministically.
            rows, features, mask, split = build(args.samples, args.out, args.seed)
    else:
        (args.out / "config.json").write_text(json.dumps(config, indent=2))
        rows, features, mask, split = build(args.samples, args.out, args.seed)
    train, valid, test = [np.flatnonzero(split == i) for i in range(3)]
    if any(not len(ids) for ids in (train, valid, test)):
        raise ValueError("Need nonempty train/validation/test splits")
    net, optimizer = Network(inputs=SIZE, hidden=(64, 32), seed=args.seed), None
    if args.initial_policy and not args.resume:
        initial = Network.load(args.initial_policy)
        for target, source in zip(net.parameters(), initial.parameters(), strict=True):
            if target.value.shape != source.value.shape:
                raise ValueError("Initial policy architecture mismatch")
            target.value[:] = source.value
    optimizer = Adam(net.parameters(), lr=args.learning_rate)
    rng, logs, epoch_start = np.random.default_rng(args.seed), [], 0
    if args.resume:
        with np.load(args.out / "last.npz", allow_pickle=False) as ck:
            for i, param in enumerate(net.parameters()):
                param.value[:] = ck[f"p{i}"]
                optimizer.m[i][:] = ck[f"m{i}"]
                optimizer.v[i][:] = ck[f"v{i}"]
            optimizer.t, epoch_start = int(ck["t"]), int(ck["epoch"])
            rng.bit_generator.state = json.loads(str(ck["rng"]))
        logs = json.loads((args.out / "metrics.json").read_text())["epochs"]
    best, stale = min((r["validation"]["cross_entropy"] for r in logs), default=float("inf")), 0
    for epoch in range(epoch_start, args.epochs):
        started = time.perf_counter()
        indices = rng.permutation(train)
        total = 0.0
        for offset in range(0, len(indices), 128):
            ids = indices[offset : offset + 128]
            x = np.asarray(features[ids], dtype=np.float32)
            optimizer.zero_grad()
            prediction = net.forward(x.reshape(-1, SIZE)).reshape(len(ids), 5)
            loss, gradient = choice_loss(prediction, mask[ids])
            net.backward(gradient.reshape(-1, 1))
            optimizer.step()
            total += loss * len(ids)
        validation = evaluate(net, features, mask, valid)
        if not np.isfinite(validation["cross_entropy"]):
            raise RuntimeError("Non-finite policy training")
        row = {
            "epoch": epoch + 1,
            "train_cross_entropy": total / len(train),
            "validation": validation,
            "seconds": time.perf_counter() - started,
        }
        logs.append(row)
        if validation["cross_entropy"] < best:
            best, stale = validation["cross_entropy"], 0
            net.save(args.out / "best.npz")
        else:
            stale += 1
        checkpoint(args.out / "last.npz", net, optimizer, epoch + 1, rng)
        (args.out / "metrics.json").write_text(json.dumps({"epochs": logs}, indent=2))
        print(json.dumps(row), flush=True)
        if stale >= 3:
            break
    net = Network.load(args.out / "best.npz")
    report = {
        "sampled_choices": evaluate(net, features, mask, test),
        "full_legal_choices": full_legal_test(
            PlayerPolicy(args.out / "best.npz"), rows, test, args.seed
        ),
        "sample_years": dict(Counter(row.get("date", "unknown")[:4] for row in rows)),
        "splits": {"train": len(train), "validation": len(valid), "test": len(test)},
        "weights_sha256": hashlib.sha256((args.out / "best.npz").read_bytes()).hexdigest(),
    }
    (args.out / "evaluation.json").write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
