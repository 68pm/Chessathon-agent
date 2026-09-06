from types import SimpleNamespace

import pytest

from scripts.alien_rating_ladder import engine_options, summarize


def test_unsupported_rating_is_rejected_instead_of_clamped():
    engine = SimpleNamespace(
        options={
            "UCI_Elo": SimpleNamespace(min=1320, max=3190),
            "UCI_LimitStrength": True,
        }
    )
    with pytest.raises(ValueError, match="outside"):
        engine_options(engine, [900, 1500])
    assert engine_options(engine, [1500])["UCI_LimitStrength"]


def test_highest_win_excludes_draws_and_invalid_opponent_failures():
    games = [
        {"opponent_elo": 1500, "score": 1, "termination": "checkmate"},
        {"opponent_elo": 1500, "score": 0, "termination": "checkmate"},
        {"opponent_elo": 1700, "score": 0.5, "termination": "threefold_repetition"},
        {"opponent_elo": 1900, "score": None, "termination": "invalid"},
    ]
    summary = summarize(games, [1500, 1700, 1900])
    assert summary["highest_nominal_level_defeated"] == 1500
    assert summary["highest_level_with_majority_score"] is None
    assert summary["invalid_games"] == 1
    assert (summary["wins"], summary["draws"], summary["losses"]) == (1, 1, 1)
