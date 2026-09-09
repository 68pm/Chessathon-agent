import chess
import numpy as np

from training.calibrated_value_head import active, ridge_head


def test_ridge_sign_units_and_prior_are_preserved():
    hidden = np.eye(2)
    prior = np.array([20., -30.])
    target = np.array([-800., 600.])
    weights = np.array([200., 100.])
    result = ridge_head(hidden, target, weights, prior)
    np.testing.assert_allclose(result, (weights * target + 50 * prior) / (weights + 50))
    np.testing.assert_array_equal(prior, [20., -30.])
    assert result[0] < 0 < result[1]


def test_runtime_region_excludes_early_game_and_low_material():
    board = chess.Board()
    assert not active(board)
    board.fullmove_number = 13
    assert active(board)
    assert not active(chess.Board('8/8/8/3k4/8/4K3/8/8 w - - 0 30'))
