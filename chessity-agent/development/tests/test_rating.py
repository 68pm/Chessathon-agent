import pytest

from scripts.rating_benchmark import fit_rating, summarize


def test_logistic_rating_known_results_and_no_finite_boundary():
    assert fit_rating([{"score": 0.5, "opponent_elo": 1500}]) == pytest.approx(1500)
    rows = [{"score": s, "opponent_elo": 1600} for s in [1, 1, 1, 0]]
    assert fit_rating(rows) == pytest.approx(1790.8485019)
    assert fit_rating([{"score": 0, "opponent_elo": 1500}]) is None


def test_small_sample_band_is_not_degenerate():
    rows = [
        {"agent": "synthetic", "pair": 0, "score": score, "opponent_elo": 1500} for score in [1, 0]
    ]
    summary = summarize(rows)["synthetic"]
    low, high = summary["approximate_uncertainty_envelope"]
    assert low < 1200 < 1800 < high
    assert summary["descriptive_pair_bootstrap_95"] == [None, None]
