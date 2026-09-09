import chess
import numpy as np
import pytest
from training.progression_context_head import features, solve_box


@pytest.mark.parametrize('fen', [chess.STARTING_FEN,
    '4k3/7q/8/8/8/8/5PPP/6K1 w - - 0 1',
    '4k3/7q/8/8/6P1/7P/5P2/6K1 w - - 0 1',
    '4k3/8/3p4/4N3/8/8/8/4K3 w - - 0 1'])
def test_colour_mirror_and_turn_antisymmetry(fen):
    board = chess.Board(fen)
    assert np.array_equal(features(board), features(board.mirror()))
    changed = board.copy(); changed.turn = not board.turn
    assert np.array_equal(features(board), -features(changed))


def test_shield_gap_is_zero_for_adjacent_forward_pawns():
    board = chess.Board('4k3/7q/8/8/8/8/5PPP/6K1 w - - 0 1')
    assert features(board)[0] == 0
    board.remove_piece_at(chess.G2)
    assert features(board)[0] == -25 * 3 * 4 / 24
    board.remove_piece_at(chess.H7)
    assert features(board)[0] == 0


def test_box_fit_stationarity_and_boundary_signs():
    rng = np.random.default_rng(99)
    x = rng.normal(size=(120, 3)); y = x @ np.array([-.5, .4, 1.5])
    weights = np.ones(len(y)); penalty = .001
    coefficient = solve_box(x, y, weights, penalty)
    gradient = x.T @ (x @ coefficient - y) + penalty * coefficient
    assert np.all((0 <= coefficient) & (coefficient <= 1))
    for c, g in zip(coefficient, gradient, strict=True):
        assert (c == 0 and g >= -1e-8) or (c == 1 and g <= 1e-8) or abs(g) < 1e-8


def test_zero_information_fits_no_correction():
    assert np.array_equal(solve_box(np.zeros((10, 3)), np.zeros(10), np.ones(10)), np.zeros(3))
