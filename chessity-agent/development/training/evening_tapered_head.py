"""Original symmetric tapered linear residual for searched-position evaluation."""
import chess
import numpy as np

def features(board):
    phase=min(24,sum(len(board.pieces(p,c))*v for p,v in ((2,1),(3,1),(4,2),(5,4)) for c in (True,False)))
    x=np.zeros((2,384),dtype=np.float64)
    for square,piece in board.piece_map().items():
        relative=square if piece.color else chess.square_mirror(square)
        index=(piece.piece_type-1)*64+relative
        sign=1 if piece.color==board.turn else -1
        x[0,index]+=sign*phase/24
        x[1,index]+=sign*(24-phase)/24
    return x.reshape(768)

def predict(x,weights,blend):
    return np.clip(np.asarray(x)@np.asarray(weights).reshape(768)*blend,-250,250)

def solve(x,y,row_weights,penalty):
    gram=x.T@(x*row_weights[:,None])
    rhs=x.T@(y*row_weights)
    gram.flat[::len(gram)+1]+=penalty
    return np.linalg.solve(gram,rhs)
