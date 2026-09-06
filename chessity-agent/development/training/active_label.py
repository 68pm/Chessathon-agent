"""Offline-only deeper labelling of uncertain positions with a user-supplied UCI teacher."""

import argparse
import hashlib
import json
from pathlib import Path

import chess
import chess.engine
import numpy as np

from engine.evaluation import classical
from engine.neural import NeuralValue


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, default=Path("data/lichess-50k/dataset.npz"))
    p.add_argument(
        "--teacher", type=Path, required=True, help="Existing local UCI engine binary, offline only"
    )
    p.add_argument("--model", type=Path, default=Path("models/value.npz"))
    p.add_argument("--count", type=int, default=1000)
    p.add_argument("--seconds", type=float, default=0.1)
    p.add_argument("--out", type=Path, default=Path("data/active-labels.jsonl"))
    a = p.parse_args()
    model = NeuralValue(a.model)
    with np.load(a.data, allow_pickle=False) as data:
        # Never relabel/tune against held-out test positions.
        selected = np.flatnonzero(data["split"] == 0)
        fens, groups = data["fen"][selected], data["group"][selected]
    ranked = []
    for fen, group in zip(fens, groups):
        b = chess.Board(str(fen))
        disagreement = abs(model.centipawns(b) - classical(b))
        ranked.append((disagreement, str(fen), str(group)))
    ranked.sort(reverse=True)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    existing = set()
    if a.out.exists():
        existing = {json.loads(line)["fen"] for line in a.out.read_text().splitlines() if line}
    with chess.engine.SimpleEngine.popen_uci(str(a.teacher.resolve())) as teacher:
        if "Threads" in teacher.options:
            teacher.configure({"Threads": 1})
        with a.out.open("a") as output:
            for disagreement, fen, group in ranked[: a.count]:
                if fen in existing:
                    continue
                b = chess.Board(fen)
                info = teacher.analyse(b, chess.engine.Limit(time=a.seconds))
                cp = info["score"].pov(b.turn).score(mate_score=10000)
                output.write(
                    json.dumps(
                        {
                            "fen": fen,
                            "group": group,
                            "split": 0,
                            "cp": cp,
                            "depth": info.get("depth"),
                            "disagreement": disagreement,
                        }
                    )
                    + "\n"
                )
                output.flush()
        meta = {
            "teacher": teacher.id,
            "teacher_sha256": hashlib.sha256(a.teacher.read_bytes()).hexdigest(),
            "data_sha256": hashlib.sha256(a.data.read_bytes()).hexdigest(),
            "seconds_per_position": a.seconds,
            "requested_count": a.count,
            "purpose": "Offline training labels only; excluded from submission",
        }
    a.out.with_suffix(".metadata.json").write_text(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
