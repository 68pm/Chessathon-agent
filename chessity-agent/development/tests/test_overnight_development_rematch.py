from datetime import timedelta

import pytest

from scripts.overnight_development_rematch import DEADLINE, FAILURES, remaining_budget, unlock_next


def game(white, score, termination='checkmate', failed_colour=None):
    return dict(candidate_white=white, score=score, termination=termination, failed_colour=failed_colour)


def test_requires_complete_colour_pair_and_played_win():
    assert unlock_next([game(True, 1), game(False, 0)])
    assert unlock_next([game(True, .5), game(False, 1)])
    assert not unlock_next([game(True, 1)])
    assert not unlock_next([game(True, 1), game(True, 0)])
    assert not unlock_next([game(True, .5), game(False, .5)])


@pytest.mark.parametrize('failure', sorted(FAILURES))
def test_either_side_failure_prevents_ascent(failure):
    assert not unlock_next([game(True, 1), game(False, 0, failure)])
    assert not unlock_next([game(True, 1, failure), game(False, 0)])


def test_explicit_failure_prevents_ascent():
    assert not unlock_next([game(True, 1), game(False, 0, failed_colour='black')])


def test_reserves_entire_pair_before_cutoff():
    assert remaining_budget(DEADLINE - timedelta(seconds=2700))
    assert not remaining_budget(DEADLINE - timedelta(seconds=2699))
    assert not remaining_budget(DEADLINE)
