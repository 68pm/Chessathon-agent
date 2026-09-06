"""Verify archive checksums, complete exports and sampled real-game provenance."""

import hashlib
import io
import json
from pathlib import Path

import chess.pgn

from scripts.alien_rating_ladder import save_json, sha256


def main():
    run = Path("runs/magnus-mixed-20260906")
    history = Path("data/magnuscarlsen-history")
    status = json.loads((history / "download-status.json").read_text())
    snapshot = history / json.loads((history / "latest.json").read_text())["export"]
    export = json.loads((snapshot / "manifest.json").read_text())
    assert status["status"] == "complete" and export["status"] == "complete"
    assert len(status["months"]) == status["archives_listed"] == len(export["sources"])
    for source in export["sources"]:
        assert sha256(source["file"]) == source["sha256"]
    assert sum(p["games"] for p in export["parts"]) == export["unique_games"]
    assert all(0 < p["games"] <= 50 for p in export["parts"])
    for part in export["parts"]:
        for source in part["files"]:
            assert sha256(snapshot / source["file"]) == source["sha256"]
    assert sha256(snapshot / export["combined"]["file"]) == export["combined"]["sha256"]
    rows = [json.loads(line) for line in (run / "mixture/samples.jsonl").read_text().splitlines()]
    keys, splits = set(), {}
    for row in rows:
        key = " ".join(row["fen"].split()[:4])
        assert key not in keys
        keys.add(key)
        assert splits.setdefault(row["game_id"], row["split"]) == row["split"]
    selected = sorted(
        (r for r in rows if r["player"] == "magnuscarlsen"),
        key=lambda r: hashlib.sha256((r["game_id"] + r["fen"]).encode()).hexdigest(),
    )[:100]
    remaining = {(r["game_id"], r["fen"], r["played_uci"]) for r in selected}
    source_records = []
    for source in export["sources"]:
        for record in json.loads(Path(source["file"]).read_text())["games"]:
            headers = chess.pgn.read_headers(io.StringIO(record["pgn"]))
            link = headers.get("Link", "")
            uid = hashlib.sha256(link.encode()).hexdigest()
            if uid not in {r[0] for r in remaining}:
                continue
            game = chess.pgn.read_game(io.StringIO(record["pgn"]))
            assert not game.errors
            board = game.board()
            for move in game.mainline_moves():
                match = (uid, board.fen(), move.uci())
                if match in remaining:
                    assert headers["White" if board.turn else "Black"].lower() == "magnuscarlsen"
                    remaining.remove(match)
                    source_records.append(
                        {"url": link, "game_id": uid, "fen": board.fen(), "played_uci": move.uci()}
                    )
                board.push(move)
    assert not remaining
    report = {
        "archive_months_verified": len(export["sources"]),
        "games": export["unique_games"],
        "parts_verified": len(export["parts"]),
        "missing_pgn": export["missing_pgn_games"],
        "all_checksums_match": True,
        "positions": len(rows),
        "normalized_fen_duplicates": 0,
        "cross_split_game_overlap": 0,
        "sampled_magnus_moves_traced_to_raw_archive": source_records,
        "scope": status["scope"],
        "history_export": str(snapshot),
    }
    save_json(run / "data-audit.json", report)
    print(
        json.dumps(
            {k: v for k, v in report.items() if k != "sampled_magnus_moves_traced_to_raw_archive"},
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
