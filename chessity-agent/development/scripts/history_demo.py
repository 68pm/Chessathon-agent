"""Run the full offline workflow on generated games; never fetch player history."""

import json
import random
from pathlib import Path

import chess
import chess.pgn

from engine.openings import ALIEN_LINE
from training.history_batches import collect, write_json


def main():
    player = "synthetic-player"
    prefix = f"https://api.chess.com/pub/player/{player}/games/"
    out = Path("runs/history-batch-demo")
    games = []
    for number in range(122):
        board = chess.Board()
        if number % 4 == 0:
            for san in ALIEN_LINE:
                board.push_san(san)
        rng = random.Random(number + 20260906)
        for _ in range(24):
            if board.is_game_over():
                break
            board.push(rng.choice(list(board.legal_moves)))
        game = chess.pgn.Game.from_board(board)
        game.headers.update(
            {
                "Event": "GENERATED SOFTWARE TEST DATA",
                "White": player,
                "Black": "synthetic-opponent",
                "Round": str(number),
                "Result": ["1-0", "0-1", "1/2-1/2"][number % 3],
            }
        )
        games.append({"uuid": f"synthetic-{number}", "pgn": str(game), "rules": "chess"})
    games.append({"uuid": "synthetic-no-pgn", "rules": "chess"})
    write_json(
        out / "archives.json",
        {
            "archives": [prefix + "2026/01", prefix + "2026/02"],
            "provenance": "Synthetic local fixtures; no network request",
        },
    )
    write_json(out / "months/2026-01.json", {"games": games[:60]})
    write_json(out / "months/2026-02.json", {"games": games[60:] + games[:5]})

    def forbidden(*_args):
        raise AssertionError("Demo must never make a network request")

    status = collect(player, out, "", "offline demo", offline=True, request=forbidden, delay=0)
    snapshot = out / status["export"]
    manifest = json.loads((snapshot / "manifest.json").read_text())
    summary = {
        "provenance": "Generated test games, not Witty_Alien or any real player's history. Synthetic result headers are test labels, not measured games or rating evidence.",
        "unique_records": status["unique_games"],
        "duplicate_records_removed": manifest["duplicates_removed"],
        "part_sizes": [p["games"] for p in manifest["parts"]],
        "missing_pgn_records": manifest["missing_pgn_games"],
        "analysis": json.loads((snapshot / "style-analysis.json").read_text()),
        "samples": json.loads((snapshot / "style-samples.manifest.json").read_text()),
        "network_requests": 0,
    }
    write_json(Path("docs/evidence/history-batch-demo.json"), summary)
    print(
        json.dumps(
            {
                "parts": summary["part_sizes"],
                "duplicates_removed": summary["duplicate_records_removed"],
                "training_examples_prepared": status["training_positions_prepared"],
                "network_requests": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
