import json

import chess
import chess.pgn

from engine.openings import ALIEN_LINE
from training.chesscom_history import export_games
from training.style_analysis import analyze


def test_generated_games_deduplicate_and_detect_alien(tmp_path):
    board = chess.Board()
    for san in ALIEN_LINE:
        board.push_san(san)
    game = chess.pgn.Game.from_board(board)
    game.headers.update({"White": "synthetic-player", "Black": "synthetic-opponent", "Result": "*"})
    raw = tmp_path / "month.json"
    raw.write_text(
        json.dumps(
            {
                "games": [
                    {"uuid": "same", "pgn": str(game)},
                    {"uuid": "same", "pgn": str(game)},
                    {"uuid": "missing"},
                ]
            }
        )
    )
    pgn = tmp_path / "export.pgn"
    counts = export_games([raw], pgn)
    assert counts == {
        "unique_games": 2,
        "pgn_games": 1,
        "missing_pgn_games": 1,
        "duplicates_removed": 1,
    }
    report = analyze([pgn, pgn], "synthetic-player")
    assert report["counts"]["games"] == 1
    assert report["counts"]["alien_sacrifices"] == 1
    assert report["counts"]["alien_opportunities"] == 1
    assert report["counts"]["duplicate_games_skipped"] == 1
    assert report["counts"]["unfinished"] == 1
