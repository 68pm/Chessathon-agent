"""Deterministic, resumable supervised learning from scratch. CPU only."""

import os

for variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
    os.environ[variable] = "1"

import argparse
import hashlib
import json
import time
from pathlib import Path

import chess
import numpy as np

from nn.losses import huber
from nn.model import Network
from nn.optim import Adam


def checkpoint(path, net, optimizer, epoch, rng):
    payload = {f"p{i}": p.value for i, p in enumerate(net.parameters())}
    payload.update({f"m{i}": v for i, v in enumerate(optimizer.m)})
    payload.update({f"v{i}": v for i, v in enumerate(optimizer.v)})
    payload.update(
        t=np.array(optimizer.t),
        epoch=np.array(epoch),
        rng=np.array(json.dumps(rng.bit_generator.state)),
    )
    temporary = path.with_suffix(".tmp.npz")
    np.savez(temporary, **payload)
    temporary.replace(path)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, default=Path("data/lichess-50k/dataset.npz"))
    p.add_argument("--out", type=Path, default=Path("runs/value-128"))
    p.add_argument("--epochs", type=int, default=12)
    p.add_argument("--batch-size", type=int, default=256)
    p.add_argument("--seed", type=int, default=20260905)
    p.add_argument("--hidden", type=int, default=128)
    p.add_argument("--resume", action="store_true")
    p.add_argument("--hard-mining", action="store_true")
    p.add_argument("--curriculum", action="store_true")
    p.add_argument("--aux-weight", type=float, default=0)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    with np.load(a.data, allow_pickle=False) as data:
        x, y, split = data["x"], data["y"], data["split"]
        fens = data["fen"] if a.aux_weight else None
    if a.aux_weight:
        from training.style_targets import pressure_target

        auxiliary = np.array(
            [pressure_target(chess.Board(str(fen))) for fen in fens], dtype=np.float32
        )[:, None]
        y = np.concatenate([y, auxiliary], axis=1)
    train, valid = np.flatnonzero(split == 0), np.flatnonzero(split == 1)
    if len(train) == 0 or len(valid) == 0:
        raise ValueError("Training and validation sets must both be nonempty")
    rng = np.random.default_rng(a.seed)
    net, epoch_start = Network(hidden=(a.hidden, 32), seed=a.seed, outputs=y.shape[1]), 0
    optimizer = Adam(net.parameters())
    logs = []
    config = {
        "seed": a.seed,
        "hidden": a.hidden,
        "batch_size": a.batch_size,
        "curriculum": a.curriculum,
        "hard_mining": a.hard_mining,
        "aux_weight": a.aux_weight,
        "dataset_sha256": hashlib.sha256(a.data.read_bytes()).hexdigest(),
    }
    if a.resume:
        old_config = json.loads((a.out / "config.json").read_text())
        old_config.setdefault("aux_weight", 0)
        if old_config != config:
            raise ValueError("Resume configuration/data does not match checkpoint")
        with np.load(a.out / "last.npz", allow_pickle=False) as ck:
            for i, param in enumerate(net.parameters()):
                param.value[:] = ck[f"p{i}"]
                optimizer.m[i][:] = ck[f"m{i}"]
                optimizer.v[i][:] = ck[f"v{i}"]
            optimizer.t, epoch_start = int(ck["t"]), int(ck["epoch"])
            rng.bit_generator.state = json.loads(str(ck["rng"]))
        logs = json.loads((a.out / "metrics.json").read_text())["epochs"]
    (a.out / "config.json").write_text(json.dumps(config, indent=2))
    baseline = float(np.mean(y[valid, :1] ** 2))
    best = min((row["validation_mse"] for row in logs), default=float("inf"))
    stale = 0
    for epoch in range(epoch_start, a.epochs):
        started = time.monotonic()
        indices = train.copy()
        if a.curriculum and epoch < 2:
            indices = indices[np.abs(y[indices, 0]) > 0.25]
        if a.hard_mining and epoch > 1:
            errors = np.concatenate(
                [
                    np.abs(net.forward(x[train[i : i + 512]]) - y[train[i : i + 512]])[:, 0]
                    for i in range(0, len(train), 512)
                ]
            )
            prob = 0.5 / len(train) + 0.5 * (errors + 0.01) / (errors + 0.01).sum()
            indices = rng.choice(train, size=len(train), replace=True, p=prob)
        rng.shuffle(indices)
        loss_sum = 0
        for offset in range(0, len(indices), a.batch_size):
            batch = indices[offset : offset + a.batch_size]
            optimizer.zero_grad()
            prediction = net.forward(x[batch])
            loss, value_gradient = huber(prediction[:, :1], y[batch, :1])
            gradient = np.zeros_like(prediction)
            gradient[:, :1] = value_gradient
            if a.aux_weight:
                auxiliary_loss, auxiliary_gradient = huber(prediction[:, 1:], y[batch, 1:])
                gradient[:, 1:] = a.aux_weight * auxiliary_gradient
                loss += a.aux_weight * auxiliary_loss
            net.backward(gradient)
            optimizer.step()
            loss_sum += loss * len(batch)
        pred = np.concatenate(
            [net.forward(x[valid[i : i + 512]]) for i in range(0, len(valid), 512)]
        )
        mse = float(np.mean((pred[:, :1] - y[valid, :1]) ** 2))
        row = {
            "epoch": epoch + 1,
            "train_huber": loss_sum / len(indices),
            "validation_mse": mse,
            "validation_mae": float(np.mean(np.abs(pred[:, :1] - y[valid, :1]))),
            "seconds": time.monotonic() - started,
        }
        if not np.isfinite(mse):
            raise RuntimeError("Non-finite training result")
        logs.append(row)
        if mse < best:
            best, stale = mse, 0
            net.save(a.out / "best.npz")
        else:
            stale += 1
        checkpoint(a.out / "last.npz", net, optimizer, epoch + 1, rng)
        (a.out / "metrics.json").write_text(
            json.dumps({"zero_predictor_validation_mse": baseline, "epochs": logs}, indent=2)
        )
        print(json.dumps(row), flush=True)
        if stale >= 4:
            break


if __name__ == "__main__":
    main()
