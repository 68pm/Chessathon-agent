import chess
import numpy as np

from training.daytime_signed_value import (
    cohorts_pass,
    correction_cohorts,
    forward,
    gradients,
    select_targets,
    signed_parameters,
    update_hidden,
)


def test_signed_head_can_represent_opposite_corrections():
    p = signed_parameters(np.random.default_rng(9))
    p[0].fill(0)
    p[1].fill(0)
    p[0][0, 0], p[0][1, 4] = 1, 1
    x = np.zeros((2, 768), dtype=np.float32)
    x[0, 0], x[1, 1] = 1, 1
    assert np.array_equal(forward(x, p)[0] * 200, [125, -125])


def test_training_step_preserves_readout_and_learns_both_signs():
    p = signed_parameters(np.random.default_rng(10))
    x = np.zeros((2, 768), dtype=np.float32)
    x[0, 0], x[1, 1] = 1, 1
    y = np.array([.3, -.3], dtype=np.float32)
    before = abs(forward(x, p)[0] - y)
    output = p[2].copy()
    m, v = [np.zeros_like(a) for a in p], [np.zeros_like(a) for a in p]
    for step in range(1, 21):
        gradient = gradients(x, y, p)
        update_hidden(p, m, v, gradient, gradient, step)
    assert np.array_equal(p[2], output)
    assert np.all(abs(forward(x, p)[0] - y) < before)


def test_one_sided_average_gain_cannot_hide_wrong_direction_errors():
    base = np.zeros(150)
    cp = np.array([-100.] * 50 + [200.] * 100)
    assert not cohorts_pass(correction_cohorts(base, cp, np.full(150, 50.)))
    assert cohorts_pass(correction_cohorts(base, cp, np.array([-50.] * 50 + [50.] * 100)))


def test_conflicting_mirror_labels_are_excluded_and_consistent_duplicates_kept_once():
    a = dict(id='a', eligible=True, fen=chess.STARTING_FEN, start_fen=chess.STARTING_FEN,
             history=[], target_stm_cp=0.)
    mirror = chess.Board().mirror().fen()
    b = dict(a, id='b', fen=mirror, start_fen=mirror, target_stm_cp=300.)
    selected, excluded = select_targets([dict(status='complete', rows=[a,b])])
    assert not selected and len(excluded['conflicting_keys']) == 1
    b['target_stm_cp'] = 40.
    selected, excluded = select_targets([dict(status='complete', rows=[a,b])])
    assert selected == [a] and excluded['duplicate_ids'] == ['b']
