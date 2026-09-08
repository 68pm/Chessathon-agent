import chess
import numpy as np

from training.rule_value import arrays, features, loss_and_gradients


def test_huber_gradient_finite_difference():
    rng = np.random.default_rng(84)
    x = rng.uniform(0, .2, (7, 9))
    p = [rng.uniform(-.1, .1, (9, 4)), np.array([.3, .7, -.2, 1.3]),
         np.array([.2, -.3, .4, .1])]
    target = np.array([0., 2., -3., .2, .9, -2., -.4])
    _, gradients = loss_and_gradients(x, target, p)
    for param, gradient in zip(p, gradients, strict=True):
        for index in np.ndindex(param.shape):
            original, epsilon = param[index], 1e-6
            param[index] = original + epsilon
            plus = loss_and_gradients(x, target, p)[0]
            param[index] = original - epsilon
            minus = loss_and_gradients(x, target, p)[0]
            param[index] = original
            np.testing.assert_allclose(gradient[index], (plus - minus) / (2 * epsilon), atol=1e-8)


def test_rules_mirror_and_legal_ep():
    fens = [chess.STARTING_FEN, 'r3k2r/8/8/8/8/8/8/R3K2R b Kq - 23 40',
            '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 20',
            'k3r3/8/8/3pP3/8/8/8/4K3 w - d6 0 20']
    for fen in fens:
        board = chess.Board(fen)
        np.testing.assert_array_equal(features(board), features(board.mirror()))
    assert features(chess.Board(fens[2]))[772 + 3] == 1
    assert features(chess.Board(fens[3]))[772:780].sum() == 0  # pinned pawn
    x = features(chess.Board(fens[1]))
    np.testing.assert_array_equal(x[768:772], [0, 1, 1, 0])
    np.testing.assert_allclose(x[780], 23 / 70)


def test_piece_and_state_perspective():
    board = chess.Board('4k3/8/8/8/8/8/4p3/4K3 b - - 17 50')
    x = features(board)
    assert x[52] == 1  # black pawn e2 becomes own e7
    assert x[11 * 64 + 60] == 1  # opposing white king e1 becomes e8
    b, s = arrays(board)
    assert b[20] == -1 and b[4] == 6 and b[116] == -6
    np.testing.assert_array_equal(s, [-1, 0, -1, 17, 4, 116])
