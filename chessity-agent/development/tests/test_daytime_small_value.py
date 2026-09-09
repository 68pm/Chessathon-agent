"""Numerical gradient and perspective guards for the small value pilot."""
import chess
import numpy as np
import pytest

from training.daytime_small_value import active, features, forward, gradients


def test_eight_unit_gradients_against_independent_finite_differences():
    rng = np.random.default_rng(402)
    x = rng.uniform(0, .1, (5, 12))
    params = [rng.normal(0, .02, (12, 8)), np.full(8, .4), rng.normal(0, .2, 8)]
    target = np.array([.1, -.2, .3, 2., -2.])
    analytic = gradients(x, target, params)
    def loss():
        error = np.abs(forward(x, params)[0] - target)
        return np.mean(np.where(error <= 1, .5 * error**2, error - .5))
    for index in range(3):
        for slot in (0, params[index].size // 2, params[index].size - 1):
            old = params[index].flat[slot]
            params[index].flat[slot] = old + 1e-5
            right = loss()
            params[index].flat[slot] = old - 1e-5
            left = loss()
            params[index].flat[slot] = old
            assert analytic[index].flat[slot] == pytest.approx((right - left) / 2e-5, abs=1e-8)


@pytest.mark.parametrize('fen', [chess.STARTING_FEN,
    'r1bq1rk1/pp2bppp/2np1n2/2p1p3/2B1P3/2NP1N2/PPP2PPP/R1BQ1RK1 w - - 0 8'])
def test_colour_mirror_keeps_side_to_move_features(fen):
    board = chess.Board(fen)
    assert np.array_equal(features(board)[:768], features(board.mirror())[:768])


def test_classical_endgame_and_repetition_are_excluded_from_fit():
    assert not active(chess.Board('7k/8/8/8/8/8/4R3/6K1 w - - 0 1'))
    board = chess.Board()
    for uci in ('g1f3', 'g8f6', 'f3g1', 'f6g8'):
        board.push_uci(uci)
    assert board.is_repetition(2) and not active(board)
