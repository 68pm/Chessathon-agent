"""Check the perspective transform and independent numerical derivatives."""
import chess
import numpy as np

from training.daytime_antisymmetric import forward, loss_and_gradients, opposite_features
from training.rule_value import features


def test_feature_transform_matches_reversed_piece_perspective():
    board = chess.Board()
    for move in ('d2d4','g8f6','c2c4','e7e6','g1f3','d7d5'):
        board.push_uci(move)
    original = features(board)[:768]
    board.turn = not board.turn
    assert np.array_equal(opposite_features(original), features(board)[:768])
    assert np.array_equal(opposite_features(opposite_features(original)), original)


def test_prediction_is_antisymmetric():
    rng = np.random.default_rng(81)
    x = rng.uniform(0,.1,(4,768))
    parameters = [rng.normal(0,.02,(768,8)), np.full(8,.25),
        np.array([.625]*4+[-.625]*4)]
    assert np.allclose(forward(x,parameters)[0],-forward(opposite_features(x),parameters)[0],atol=1e-12)


def test_analytic_gradient_matches_finite_differences():
    rng = np.random.default_rng(82)
    x = rng.uniform(0,.05,(3,768))
    parameters = [rng.normal(0,.01,(768,8)), np.full(8,.25),
        np.array([.625]*4+[-.625]*4)]
    target = np.array([.2,-.5,1.4])
    _, gradients = loss_and_gradients(x,target,parameters)
    for part,index in ((0,(32,3)),(0,(745,6)),(1,(2,)),(2,(5,))):
        saved = parameters[part][index]
        step = 1e-5
        parameters[part][index] = saved+step
        plus = loss_and_gradients(x,target,parameters)[0]
        parameters[part][index] = saved-step
        minus = loss_and_gradients(x,target,parameters)[0]
        parameters[part][index] = saved
        assert np.isclose(gradients[part][index],(plus-minus)/(2*step),rtol=1e-5,atol=1e-9)
