"""Record actual opening-arena decisions and descriptive move counts."""

import io
import json
from pathlib import Path

import chess.pgn

from training.style_analysis import analyze


def main():
    raw = Path("runs/alien-opening-arena.json").read_text()
    data = json.loads(raw)
    games, names = [], set()
    for row in data["games"]:
        game = chess.pgn.read_game(io.StringIO(row["pgn"]))
        assert game and not game.errors
        if row["candidate"].startswith("alien-"):
            assert next(iter(game.mainline_moves())).uci() == "g5f7"
        game.headers["White"] = row["candidate"]
        game.headers["Black"] = row["opponent"]
        games.append(str(game))
        names.add(row["candidate"])
    path = Path("docs/evidence/alien-opening-arena.pgn")
    path.write_text("\n\n".join(games) + "\n", encoding="utf-8")
    path.with_suffix(".json").write_text(raw)
    reports = {name: analyze([path], name) for name in sorted(names)}
    Path("docs/evidence/alien-style-counts.json").write_text(json.dumps(reports, indent=2))
    print(
        json.dumps(
            {
                name: {"counts": row["counts"], "rates": row["rates"]}
                for name, row in reports.items()
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
