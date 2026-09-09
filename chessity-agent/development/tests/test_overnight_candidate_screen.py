"""Stop rules prevent partial pairs and operational wins from unlocking ratings."""

import pytest

from scripts.overnight_candidate_screen import advance, comparison_passes


def game(score, white=True, termination='checkmate', failed_colour=None):
    return dict(score=score, candidate_white=white, termination=termination, failed_colour=failed_colour)


@pytest.mark.parametrize('scores,expected', [([1, 1, 0, 0], True), ([1, .5, .5, 0], True),
    ([1, 0, 0, 0], False), ([.5, .5, .5, .5], False), ([1, 1], False)])
def test_four_games_need_half_points_and_a_played_win(scores, expected):
    assert comparison_passes([game(s, bool(i % 2)) for i, s in enumerate(scores)]) == expected


@pytest.mark.parametrize('termination', ['init', 'flag', 'illegal', 'crash', 'both_failed'])
def test_operational_failure_blocks_comparison_and_does_not_unlock_rated_pair(termination):
    bad = game(1, termination=termination, failed_colour='black')
    assert not comparison_passes([bad, game(1), game(1), game(0)])
    assert not advance([bad, game(0, False)])


def test_ascent_finishes_both_colours_and_stops_without_a_clean_win():
    assert not advance([game(1)])
    assert not advance([game(1), game(0)])
    assert not advance([game(.5), game(.5, False)])
    assert advance([game(1), game(0, False)])
