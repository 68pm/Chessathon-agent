import random
import chess
import numpy as np
import pytest
from training.evening_tapered_head import features,predict,solve

@pytest.mark.parametrize('seed',range(5))
def test_colour_symmetry_and_independent_scalar_evaluation(seed):
    rng=random.Random(20260909100+seed);nrng=np.random.default_rng(seed)
    weights=nrng.normal(0,10,(2,6,64));board=chess.Board()
    for _ in range(90):
        phase=min(24,sum(len(board.pieces(p,c))*v for p,v in ((2,1),(3,1),(4,2),(5,4)) for c in (True,False)))
        expected=0
        for square,piece in board.piece_map().items():
            sq=square if piece.color else square^56
            expected+=(1 if piece.color==board.turn else -1)*(weights[0,piece.piece_type-1,sq]*phase+weights[1,piece.piece_type-1,sq]*(24-phase))/24
        x=features(board)
        assert np.array_equal(x,features(board.mirror()))
        assert np.isclose(predict(x,weights,.5),np.clip(expected*.5,-250,250))
        copy=board.copy(stack=False);copy.turn=not copy.turn
        assert np.array_equal(features(copy),-x)
        if board.is_game_over():board=chess.Board()
        else:board.push(rng.choice(list(board.legal_moves)))

def test_weighted_ridge_stationarity():
    rng=np.random.default_rng(20);x=rng.normal(size=(50,8));y=rng.normal(size=50);w=rng.uniform(.5,4,size=50)
    penalty=10;beta=solve(x,y,w,penalty)
    gradient=x.T@(w*(x@beta-y))+penalty*beta
    assert np.max(abs(gradient))<1e-10

def test_prediction_cap_is_symmetric():
    x=np.ones((2,768));x[1]*=-1
    assert list(predict(x,np.ones(768),1))==[250,-250]
