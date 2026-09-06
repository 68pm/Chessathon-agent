import chess
import pytest

from training.mixed_player_samples import merge_sources


def row(game, split, move="e2e4", fen=chess.STARTING_FEN):
    return {"game_id": game, "split": split, "fen": fen, "played_uci": move}


def test_merge_preserves_old_split_and_removes_cross_player_fen_duplicate():
    old = row("old", "train")
    new = row("new", "test", "d2d4")
    rows, skipped = merge_sources([("witty", [old]), ("magnus", [new])])
    assert len(rows) == 1 and rows[0]["split"] == "train"
    assert rows[0]["player"] == "witty" and skipped == {"magnus": 1}


def test_merge_rejects_shared_game_split_leakage_and_illegal_labels():
    with pytest.raises(ValueError, match="different splits"):
        merge_sources([("witty", [row("same", "train")]), ("magnus", [row("same", "test")])])
    with pytest.raises(ValueError, match="Illegal"):
        merge_sources([("magnus", [row("bad", "train", "e2e5")])])
