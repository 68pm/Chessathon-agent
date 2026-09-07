import pytest

from scripts.improvement_review import paired_bound


def games(pairs, score=1):
    return [dict(pair=p, opening_group=f'group{p}', candidate_white=white, score=score)
            for p in range(pairs) for white in [True, False]]


def test_uniform_small_screen_cannot_create_certainty():
    assert paired_bound(games(4), 1)['lower_score_bound'] < .5
    assert .5 < paired_bound(games(12), 1)['lower_score_bound'] < 1
    assert paired_bound(games(12, .5), 1)['lower_score_bound'] < .5
    assert paired_bound(games(12), 2)['lower_score_bound'] < paired_bound(games(12), 1)['lower_score_bound']


def test_incomplete_and_duplicate_groups_rejected():
    with pytest.raises(AssertionError):
        paired_bound(games(4)[:-1], 1)
    rows = games(4)
    rows[-1]['opening_group'] = rows[-2]['opening_group'] = 'group0'
    with pytest.raises(AssertionError):
        paired_bound(rows, 1)
