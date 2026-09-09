import pytest

from scripts.daytime_pawn_bitboards_screen import pair_passes, qualifies_2800


def pair(scores, termination='checkmate'):
    return [dict(candidate_white=white, score=score, termination=termination, failed_colour=None)
            for white, score in zip((True, False), scores, strict=True)]


@pytest.mark.parametrize('failure', ['flag', 'illegal', 'crash', 'init', 'both_failed'])
def test_operational_wins_never_qualify(failure):
    assert not pair_passes(pair((1, 1), failure), 1.5)
    assert not qualifies_2800(pair((1, 1), failure))


def test_tie_retains_baseline_and_double_draws_do_not_advance():
    assert not pair_passes(pair((1, 0)), 1.5)
    assert not qualifies_2800(pair((.5, .5), 'threefold_repetition'))
    assert qualifies_2800(pair((1, 0)))
    assert pair_passes(pair((1, .5)), 1.5)


def test_missing_colour_and_failure_metadata_rejected():
    games = pair((1, 1))
    games[1]['candidate_white'] = True
    assert not pair_passes(games, 1.5)
    games = pair((1, 1))
    games[0]['failed_colour'] = 'black'
    assert not pair_passes(games, 1.5)
