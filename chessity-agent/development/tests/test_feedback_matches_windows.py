import json
import os

import pytest

from scripts import feedback_matches_windows as wrapper
from training.game_feedback import write_json


def test_completed_game_filter_survives_child_paths(tmp_path):
    root = wrapper.feedback_path(tmp_path) / 'nested'
    root.mkdir()
    for name in ('game-001.json', 'game-001.current.json', 'game-x.json', 'game-0123.json'):
        (root / name).write_text('{}')
    assert sorted(p.name for p in root.glob('game-*.json')) == ['game-001.json', 'game-0123.json']
    assert len(list(root.glob('*.json'))) == 4


@pytest.mark.skipif(os.name != 'nt', reason='Windows extended path handling')
def test_atomic_review_and_model_at_long_path(tmp_path):
    root = wrapper.feedback_path(tmp_path)
    while len(str(root)) < 280:
        root /= 'feedback-case-0123456789'
    target = root / 'review.json'
    write_json(target, dict(status='running'))
    write_json(target, dict(status='complete'))
    assert json.loads(target.read_text()) == {'status': 'complete'}
    assert not target.with_suffix('.json.pending').exists()
    import numpy as np
    model = root / 'player-policy.npz'
    np.savez_compressed(model, weight=np.asarray([1.0]))
    with np.load(model) as saved:
        assert saved['weight'][0] == 1.0


@pytest.mark.parametrize('fails', [False, True])
def test_calls_original_feedback_entrypoint_and_restores_roots(monkeypatch, fails):
    before = wrapper.feedback_matches.ROOT, wrapper.overnight_matches.ROOT
    called = []

    def stub():
        assert isinstance(wrapper.feedback_matches.ROOT, wrapper.FeedbackPath)
        assert isinstance(wrapper.overnight_matches.ROOT, wrapper.FeedbackPath)
        called.append(True)
        if fails:
            raise RuntimeError('recorded failure')

    monkeypatch.setattr(wrapper.feedback_matches, 'main', stub)
    if fails:
        with pytest.raises(RuntimeError, match='recorded failure'):
            wrapper.main()
    else:
        wrapper.main()
    assert called == [True]
    assert (wrapper.feedback_matches.ROOT, wrapper.overnight_matches.ROOT) == before
