"""Prevent mate or interrupted search values becoming centipawn training labels."""
from scripts.daytime_student_descendants import search_score


def test_finite_search_score_preserves_sign():
    assert search_score(-142, True) == dict(complete=True, engine_score=-142,
        mate_band=False, score_stm_cp=-142)


def test_both_mate_bands_excluded_from_cp():
    for score in (-30000, -29000, 29000, 30000):
        row = search_score(score, True)
        assert row['engine_score'] == score and row['mate_band']
        assert row['score_stm_cp'] is None


def test_interrupted_score_is_not_a_label():
    assert search_score(320, False) == dict(complete=False, engine_score=None,
        mate_band=False, score_stm_cp=None)
