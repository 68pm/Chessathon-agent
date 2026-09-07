"""Check live-blend learning, equivalent good moves and family separation."""

import numpy as np
import pytest

from training.mistake_replay import corrected, endpoint_loss_gradient, pair_loss_gradient, partition


@pytest.mark.parametrize('kind', ['endpoint', 'pair'])
def test_effective_runtime_blend_gradients(kind):
    rng = np.random.default_rng(73)
    p = [rng.normal(0, .04, (6, 3)), np.full(3, .4), np.array([.2, -.3, .1])]
    x = rng.normal(0, .4, (3, 2, 6))
    base = np.array([[100., -70.], [-30., 130.], [20., -15.]])
    signs = np.array([[1., -1.], [-1., 1.], [-1., -1.]])
    def objective():
        if kind == 'pair':
            return pair_loss_gradient(x, base, signs, np.array([.5, .8, .3]), p, .25)
        return endpoint_loss_gradient(x.reshape(6, 6), np.array([.3, -.2, .7, -.5, .2, -.8]), p, .25)
    _, gradients = objective()
    epsilon = 1e-6
    for block in range(3):
        for index in np.ndindex(p[block].shape):
            value = p[block][index]
            p[block][index] = value + epsilon
            plus = objective()[0]
            p[block][index] = value - epsilon
            minus = objective()[0]
            p[block][index] = value
            assert gradients[block][index] == pytest.approx((plus - minus) / (2 * epsilon), abs=1e-7)


def test_equivalent_move_and_two_budget_verification():
    best = [dict(cp=100, mate=None), dict(cp=120, mate=None)]
    assert corrected([dict(cp=80, mate=None), dict(cp=90, mate=None)], best)
    assert not corrected([dict(cp=80, mate=None), dict(cp=0, mate=None)], best)
    assert not corrected([dict(cp=None, mate=-3), dict(cp=None, mate=-4)], best)


def test_related_colour_pairs_stay_in_one_partition():
    rows = [dict(group=g, id=i) for i, g in enumerate(['A39'] * 8 + ['game54'] * 2 + ['game55'])]
    assigned, _ = partition(rows)
    for group in {r['group'] for r in assigned}:
        assert len({r['split'] for r in assigned if r['group'] == group}) == 1
    with pytest.raises(ValueError):
        partition([dict(group='one') for _ in range(4)])
