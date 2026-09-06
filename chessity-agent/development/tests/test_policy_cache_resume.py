"""Small synthetic regression test, excluded from real training data."""

import hashlib
import json
import sys

import chess

from training.player_policy import main


def test_finished_checkpoint_resume_rebuilds_deleted_cache_exactly(tmp_path, monkeypatch):
    board, rows = chess.Board(), []
    for index, uci in enumerate(["e2e4", "e7e5", "g1f3", "b8c6", "f1b5", "a7a6"]):
        move = chess.Move.from_uci(uci)
        rows.append(
            {
                "fen": board.fen(),
                "played_uci": uci,
                "split": ["train", "validation", "test"][index % 3],
                "gives_check": board.gives_check(move),
                "is_capture": board.is_capture(move),
            }
        )
        board.push(move)
    samples, output = tmp_path / "synthetic.jsonl", tmp_path / "policy"
    samples.write_text("\n".join(json.dumps(row) for row in rows))
    args = ["player_policy", "--samples", str(samples), "--out", str(output), "--epochs", "1"]
    monkeypatch.setattr(sys, "argv", args)
    main()
    names = ["features.npy", "labels.npz", "best.npz", "last.npz"]
    before = {name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in names}
    (output / "features.npy").unlink()
    monkeypatch.setattr(sys, "argv", args + ["--resume"])
    main()
    assert {
        name: hashlib.sha256((output / name).read_bytes()).hexdigest() for name in names
    } == before
