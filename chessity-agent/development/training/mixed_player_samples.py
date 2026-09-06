"""Combine real player decisions while preserving Witty's prior held-out splits."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import chess

from training.history_batches import load_json, write_json
from training.style_samples import prepare


def merge_sources(sources):
    selected, games, skipped = {}, {}, Counter()
    for player, rows in sources:
        for source in rows:
            row = {**source, "player": player}
            previous = games.setdefault(row["game_id"], row["split"])
            if previous != row["split"]:
                raise ValueError("Same game occurs in different splits")
            key = " ".join(row["fen"].split()[:4])
            if key in selected:
                skipped[player] += 1
                continue
            board = chess.Board(row["fen"])
            if chess.Move.from_uci(row["played_uci"]) not in board.legal_moves:
                raise ValueError("Illegal observed move")
            selected[key] = row
    return [selected[key] for key in sorted(selected)], dict(skipped)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--witty-history", type=Path, default=Path("data/witty_alien-history"))
    p.add_argument("--magnus-history", type=Path, default=Path("data/magnuscarlsen-history"))
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError("Use a fresh mixture directory")
    a.out.mkdir(parents=True)
    witty = a.witty_history / load_json(a.witty_history / "latest.json")["export"]
    magnus = a.magnus_history / load_json(a.magnus_history / "latest.json")["export"]
    magnus_samples = a.out / "magnus-uniform.jsonl"
    manifest = prepare(
        magnus / "all-available-games.pgn",
        magnus_samples,
        "magnuscarlsen",
        forcing_priority=False,
    )
    write_json(a.out / "magnus-uniform.manifest.json", manifest)
    paths = [("witty_alien", witty / "style-samples.jsonl"), ("magnuscarlsen", magnus_samples)]
    sources = [
        (player, [json.loads(line) for line in path.read_text().splitlines()])
        for player, path in paths
    ]
    rows, skipped = merge_sources(sources)
    target = a.out / "samples.jsonl"
    target.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows))
    report = {
        "sources": {
            player: {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            for player, path in paths
        },
        "positions": len(rows),
        "by_player": dict(Counter(row["player"] for row in rows)),
        "by_player_split": dict(Counter(f"{row['player']}:{row['split']}" for row in rows)),
        "games": len({row["game_id"] for row in rows}),
        "duplicate_positions_removed": skipped,
        "retained_alien_sacrifices": sum(row["alien_sacrifice"] for row in rows),
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "method": "Up to 50k per player. Retain all prior Witty samples and splits; append unique Magnus positions sampled without forcing-move priority. Equal per-position weight. Never split a source game or retain an exact normalized FEN twice. Related positions may remain across splits.",
        "authorisation_basis": "User's existing confirmation of written Chess.com authorisation and subsequent instruction to collect/train on MagnusCarlsen. Grant text not independently inspected.",
    }
    write_json(a.out / "manifest.json", report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
