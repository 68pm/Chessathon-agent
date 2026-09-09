import json

import pytest

from scripts import overnight_portable_screen as screen
from scripts.feedback_matches_windows import feedback_path
from scripts.overnight_geometry_trial import digest


def game(white, score, termination='checkmate', failed_colour=None):
    return dict(candidate_white=white, score=score, termination=termination, failed_colour=failed_colour)


def test_short_comparison_needs_points_and_clean_win():
    assert screen.comparison_passes([game(True, 1), game(False, 0), game(True, 1), game(False, 0)])
    assert not screen.comparison_passes([game(True, .5), game(False, .5)] * 2)
    assert not screen.comparison_passes([game(True, 1), game(False, 0)])


@pytest.mark.parametrize('failure', sorted(screen.FAILURES))
def test_no_operational_failure_unlocks_next_level(failure):
    assert not screen.advance([game(True, 1), game(False, 0, failure)])
    assert not screen.advance([game(True, 1, failure), game(False, 1)])


def test_ascent_requires_pair_and_played_win():
    assert screen.advance([game(True, 0), game(False, 1)])
    assert not screen.advance([game(True, 1)])
    assert not screen.advance([game(True, 1), game(True, 1)])
    assert not screen.advance([game(True, .5), game(False, .5)])
    assert not screen.advance([game(True, 1), game(False, 0, failed_colour='white')])


def test_audit_reads_long_review_paths_and_detects_tampered_checkpoint(tmp_path, monkeypatch):
    from scripts import overnight_matches
    from training import game_feedback
    root = feedback_path(tmp_path)
    while len(str(root)) < 260:
        root /= 'long-feedback-0123456789'
    root.mkdir(parents=True)
    result_path = root / 'results.json'
    result = dict(games=[dict(id=1)])
    monkeypatch.setattr(overnight_matches, 'audited', lambda path: result)
    monkeypatch.setattr(game_feedback, 'normalise_game', lambda row: (None, dict(game_key='example')))
    feedback = root / 'postgame-feedback'
    (feedback / 'completed').mkdir(parents=True)
    training = feedback / 'training.json'
    training.write_text('{}')
    (feedback / 'review.json').write_text(json.dumps(dict(status='complete')))
    (feedback / 'completed/example.json').write_text(json.dumps(dict(
        training='training.json', training_sha256=digest(training), review='review.json')))
    assert screen.audit_feedback(result_path) == result
    training.write_text('{"changed": true}')
    with pytest.raises(AssertionError):
        screen.audit_feedback(result_path)
