"""Numerical learning checks and source-family separation for the matched pilot."""

import numpy as np

from training.paired_residual import holdout_groups, opening_family, ranking


def test_pairwise_gradient_with_mixed_endpoint_perspectives():
    rng = np.random.default_rng(317)
    x = rng.uniform(0, .2, (3, 2, 5))
    base = np.array([[80., -50.], [100., 10.], [-20., 60.]])
    signs = np.array([[-1., 1.], [1., 1.], [-1., -1.]])
    margin = np.array([.5, 1., .75])
    p = [rng.normal(0, .02, (5, 3)), np.full(3, .4), rng.normal(0, .1, 3)]
    loss, grads, _ = ranking(x, base, signs, margin, p)
    for parameter, gradient, index in zip(p, grads, [(1, 2), (1,), (0,)], strict=True):
        saved, epsilon = parameter[index], 1e-5
        parameter[index] = saved + epsilon
        plus = ranking(x, base, signs, margin, p)[0]
        parameter[index] = saved - epsilon
        minus = ranking(x, base, signs, margin, p)[0]
        parameter[index] = saved
        assert abs((plus - minus) / (2 * epsilon) - gradient[index]) < 1e-7
    after = [a - .1 * g for a, g in zip(p, grads, strict=True)]
    assert ranking(x, base, signs, margin, after)[0] < loss


def test_runtime_output_clipping_stops_impossible_residual_gradient():
    x = np.ones((2, 2, 5))
    p = [np.zeros((5, 3)), np.full(3, .5), np.full(3, 10.)]
    loss, grads, gap = ranking(x, np.zeros((2, 2)), np.array([[1., 1.], [-1., 1.]]), np.ones(2), p)
    assert np.isfinite(loss) and np.allclose(gap, [0., -5.])
    assert all(np.all(g == 0) for g in grads)


def test_heldout_opening_assignment_is_count_only_and_keeps_minimums():
    groups = ['ruy-lopez'] * 8 + ['petrov'] * 4 + ['italian'] * 2
    chosen = holdout_groups(groups)
    assert chosen == holdout_groups(list(reversed(groups)))
    assert sum(g in chosen for g in groups) >= 4
    assert sum(g not in chosen for g in groups) >= 8
    assert len(set(groups) - chosen) >= 2
    assert holdout_groups(['one'] * 20) is None
    assert holdout_groups(['one', 'two', 'three']) is None


def test_same_opening_groups_across_sources_and_colours():
    ruy = ['e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1b5', 'a7a6']
    petrov = ['e2e4', 'e7e5', 'g1f3', 'g8f6']
    assert opening_family(dict(opening=ruy, candidate_white=True)) == opening_family(dict(opening=[], opening_group='C67', candidate_white=False))
    assert opening_family(dict(opening=petrov)) == opening_family(dict(opening=[], opening_group='C42'))
