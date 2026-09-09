import pytest

from scripts.feedback_screen_review import summarize, validate_ascent


def game(score, white=True, family='incumbent', termination='checkmate', failed=None):
    result = dict(candidate_path='synthetic-candidate', score=score, candidate_white=white,
        family=family, termination=termination, failed_colour=failed)
    if family.startswith('stockfish:'):
        result['elo'] = int(family.split(':')[1])
    return result


def test_operational_wins_stay_in_totals_without_inflating_highest_beaten_setting():
    games = [game(1., family='stockfish:2400'), game(0., False, 'stockfish:2400'),
        game(1., family='stockfish:2600', termination='flag', failed='black'),
        game(.5, False, 'stockfish:2600', termination='threefold_repetition')]
    report = summarize(games)
    assert report['highest_clean_nominal_win'] == 2400
    assert report['groups']['stockfish:2600']['wins'] == 1
    assert report['groups']['stockfish:2600']['clean_wins'] == 0
    assert report['groups']['stockfish:2600']['operational_games'] == 1


def test_colour_results_and_tied_comparison_are_preserved():
    games = [game(1.), game(0., False), game(1.), game(0., False)]
    report = summarize(games)
    assert report['groups']['incumbent']['by_colour']['white']['wins'] == 2
    assert report['groups']['incumbent']['by_colour']['black']['losses'] == 2
    ascent = validate_ascent([dict(label='comparison', games=games)])
    assert ascent['comparison_passed'] and ascent['comparison_signal'] == 'tied_small_sample'
    assert report['highest_clean_nominal_win'] is None


def test_nominal_display_mismatch_is_rejected():
    wrong = game(1., family='stockfish:2600')
    wrong['elo'] = 2400
    with pytest.raises(AssertionError, match='setting disagree'):
        summarize([wrong])


def test_candidate_versions_are_not_pooled():
    other = game(1.)
    other['candidate_path'] = 'different-candidate'
    with pytest.raises(AssertionError, match='versions separate'):
        summarize([game(1.), other])


@pytest.mark.parametrize('previous', [[game(.5, family='stockfish:2400'), game(.5, False, 'stockfish:2400')],
    [game(1., family='stockfish:2400'), game(0., False, 'stockfish:2400', 'init', 'black')]])
def test_no_clean_win_or_operational_failure_prevents_ascent(previous):
    stages = [dict(label='comparison', games=[game(1.), game(0., False), game(1.), game(0., False)]),
        dict(label='rated-2400', games=previous),
        dict(label='rated-2600', games=[game(1., family='stockfish:2600'), game(0., False, 'stockfish:2600')])]
    with pytest.raises(AssertionError, match='qualifying previous stage'):
        validate_ascent(stages)


def test_clean_colour_pair_permits_exact_next_level_only():
    stages = [dict(label='comparison', games=[game(1.), game(0., False), game(1.), game(0., False)]),
        dict(label='rated-2400', games=[game(1., family='stockfish:2400'), game(0., False, 'stockfish:2400')]),
        dict(label='rated-2600', games=[game(0., family='stockfish:2600'), game(0., False, 'stockfish:2600')])]
    assert validate_ascent(stages)['final_pair_qualifies_for_next'] is False
    stages[2]['label'] = 'rated-2800'
    with pytest.raises(AssertionError):
        validate_ascent(stages)
