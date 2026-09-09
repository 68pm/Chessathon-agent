import ast
import random
from pathlib import Path
import chess
import numpy as np
import pytest
from experiments import evening_queen_pawns_core as core
from experiments import daytime_move_buffers_core as base
from scripts.evening_common import ROOT
from training.rule_value import arrays

def eg_delta(board):
    phase=sum(len(board.pieces(p,c))*v for p,v in ((2,1),(3,1),(4,2),(5,4)) for c in (True,False))
    delta=0
    if phase<=8:
        for c in (True,False):
            if board.pieces(5,c) or not board.pieces(5,not c):continue
            for sq in board.pieces(1,c):
                rank=chess.square_rank(sq);file=chess.square_file(sq)
                if not any(abs(chess.square_file(e)-file)<=1 and (chess.square_rank(e)>rank if c else chess.square_rank(e)<rank)
                           for e in board.pieces(1,not c)):
                    r=rank if c else 7-rank
                    delta+=(1 if c else -1)*(-3*r*r)
    return delta*(24-min(phase,24))/24*(1 if board.turn else -1)

def check(board):
    pieces,state=arrays(board);saved=pieces.copy(),state.copy()
    for conversion in (False,True):
        a=base.classical(pieces,state,conversion);b=core.classical(pieces,state,conversion)
        # Independent delta is fractional before the evaluator's final rounding.
        assert abs((b-a)-eg_delta(board))<=1.000001
        if eg_delta(board)==0:assert a==b
        assert b==core.classical(*arrays(board.mirror()),conversion)
    assert np.array_equal(pieces,saved[0]) and np.array_equal(state,saved[1])

@pytest.mark.parametrize('seed',range(7))
def test_real_positions_and_symmetry(seed):
    board=chess.Board();rng=random.Random(2026090990+seed)
    for _ in range(180):
        check(board)
        if board.is_game_over():board=chess.Board()
        else:board.push(rng.choice(list(board.legal_moves)))

@pytest.mark.parametrize('fen',[
    '7k/1P6/8/8/8/8/6q1/K7 w - - 0 1',
    '7k/1P6/8/8/8/8/8/K7 w - - 0 1',
    '7k/1P6/8/8/8/8/6q1/KQ6 w - - 0 1',
    '1p5k/1P6/8/8/8/8/6q1/K7 w - - 0 1',
])
def test_queen_balance_and_blocked_passers(fen):check(chess.Board(fen))

def test_only_classical_changes():
    before=ast.parse((ROOT/'runs/daytime-20260909/move-buffers-01/prototype/engine/compiled_core.py').read_text())
    after=ast.parse(Path(core.__file__).read_text())
    a={n.name:ast.dump(n) for n in before.body if isinstance(n,ast.FunctionDef)}
    b={n.name:ast.dump(n) for n in after.body if isinstance(n,ast.FunctionDef)}
    assert a.keys()==b.keys() and all(a[k]==b[k] for k in a if k!='classical')
