import os

for variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
    os.environ[variable] = "1"

import argparse
import json
import time
from pathlib import Path

import chess
import numpy as np

from engine.evaluation import Evaluator, classical, style_score
from engine.neural import NeuralValue
from engine.search import Search
from nn.model import Network


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, default=Path("data/lichess-50k/dataset.npz"))
    p.add_argument("--model", type=Path, default=Path("models/value.npz"))
    p.add_argument("--out", type=Path, default=Path("runs/model-evaluation.json"))
    a = p.parse_args()
    with np.load(a.data, allow_pickle=False) as d:
        indices = np.flatnonzero(d["split"] == 2)
        x, y, fens = d["x"][indices], d["y"][indices], d["fen"][indices]
        groups = [{str(g) for g in d["group"][d["split"] == i]} for i in range(3)]
        assert not groups[0] & groups[1] and not groups[0] & groups[2] and not groups[1] & groups[2]
    if not len(x):
        raise ValueError("Empty test split")
    net = Network.load(a.model)
    started = time.perf_counter()
    model = NeuralValue(a.model)
    load_ms = (time.perf_counter() - started) * 1000
    pred = np.concatenate([net.forward(x[i : i + 512]) for i in range(0, len(x), 512)])
    sparse = np.array([model.predict_features(row) for row in x[:1000]])
    parity = float(np.max(np.abs(sparse - pred[: len(sparse), 0])))
    assert parity < 1e-5
    boards = [chess.Board(str(fen)) for fen in fens[:100]]
    calibration = []
    for low, high in zip(np.linspace(-1, 1, 11)[:-1], np.linspace(-1, 1, 11)[1:]):
        mask = (pred[:, 0] >= low) & (pred[:, 0] < high)
        if mask.any():
            calibration.append(
                {
                    "prediction_bin": [float(low), float(high)],
                    "n": int(mask.sum()),
                    "mean_prediction": float(pred[mask].mean()),
                    "mean_target": float(y[mask].mean()),
                }
            )
    report = {
        "held_out_positions": len(x),
        "mse": float(np.mean((pred - y) ** 2)),
        "mae": float(np.mean(np.abs(pred - y))),
        "zero_mse": float(np.mean(y**2)),
        "parity_max_abs": parity,
        "load_ms": load_ms,
        "calibration": calibration,
        "variants": {},
    }
    reference = None
    for mode, tolerance in [
        ("classical", 0),
        ("neural", 0),
        ("hybrid", 0),
        ("phase", 0),
        ("classical", 15),
    ]:
        evaluator = Evaluator(mode, model)
        started = time.perf_counter()
        for b in boards:
            evaluator(b)
        eval_rate = len(boards) / (time.perf_counter() - started)
        search = Search(evaluator, style_tolerance=tolerance)
        rows = []
        for b in boards[:24]:
            result = search.run(b, 0.08)
            rows.append(
                {
                    "fen": b.fen(),
                    "move": result.move.uci(),
                    "depth": result.depth,
                    "nodes": result.nodes,
                    "seconds": result.elapsed,
                    "style": style_score(b, result.move),
                    "score": result.score,
                }
            )
        name = mode if not tolerance else "style15"
        report["variants"][name] = {
            "evals_per_second": eval_rate,
            "nodes_per_second": sum(r["nodes"] for r in rows) / sum(r["seconds"] for r in rows),
            "mean_depth": float(np.mean([r["depth"] for r in rows])),
            "p95_move_ms": float(np.percentile([r["seconds"] * 1000 for r in rows], 95)),
            "mean_style": float(np.mean([r["style"] for r in rows])),
            "positions": rows,
        }
        if reference is None:
            reference = [r["move"] for r in rows]
        report["variants"][name]["root_disagreements_with_classical"] = sum(
            r["move"] != m for r, m in zip(rows, reference)
        )
    base = np.array([np.tanh(classical(b) / 600) for b in boards])
    report["classical_mse_first_100"] = float(np.mean((base - y[: len(base), 0]) ** 2))
    a.out.write_text(json.dumps(report, indent=2))
    print(
        json.dumps({k: v for k, v in report.items() if k not in ("variants", "calibration")}),
        flush=True,
    )
    for name, values in report["variants"].items():
        print(name, {k: v for k, v in values.items() if k != "positions"}, flush=True)


if __name__ == "__main__":
    main()
