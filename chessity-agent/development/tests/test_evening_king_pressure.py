import ast
import random
from pathlib import Path
import chess
import numpy as np
import pytest
from experiments import evening_king_pressure_core as core
from experiments import daytime_move_buffers_core as base
from training.rule_value import arrays
from scripts.evening_common import ROOT

def oracle(board):
    score=0
    for side in (chess.WHITE,chess.BLACK):
        if not board.pieces(chess.QUEEN,side):continue
        ring=chess.SquareSet(chess.BB_KING_ATTACKS[board.king(not side)])
        attackers=units=0
        for kind,weight in ((chess.KNIGHT,2),(chess.BISHOP,2),(chess.ROOK,3),(chess.QUEEN,5)):
            for square in board.pieces(kind,side):
                hits=len(board.attacks(square)&ring)
                if hits:attackers+=1;units+=hits*weight
        if attackers>=2:score+=(1 if side else -1)*min(250,2*units**2)
    return score*(1 if board.turn else -1)

def check(board):
    pieces,state=arrays(board)
    saved=pieces.copy(),state.copy()
    for conversion in (False,True):
        assert core.classical(pieces,state,conversion)-base.classical(pieces,state,conversion)==oracle(board)
        assert core.classical(pieces,state,conversion)==core.classical(*arrays(board.mirror()),conversion)
    assert np.array_equal(pieces,saved[0]) and np.array_equal(state,saved[1])

@pytest.mark.parametrize('seed',range(8))
def test_independent_attack_sets_and_colour_symmetry(seed):
    board=chess.Board();rng=random.Random(2026090980+seed)
    for _ in range(90):
        check(board)
        if board.is_game_over():board=chess.Board()
        else:board.push(rng.choice(list(board.legal_moves)))

@pytest.mark.parametrize('fen,expected',[
    ('R5k1/8/6Q1/8/8/8/8/K7 b - - 0 1',-250),
    ('R5k1/8/6R1/8/8/8/8/K7 b - - 0 1',0),
    ('6k1/8/6Q1/8/8/8/8/K7 b - - 0 1',0),
])
def test_cap_and_queen_gate(fen,expected):
    board=chess.Board(fen);assert oracle(board)==expected;check(board)

def test_only_classical_changes():
    before=ast.parse((ROOT/'runs/daytime-20260909/move-buffers-01/prototype/engine/compiled_core.py').read_text())
    after=ast.parse(Path(core.__file__).read_text())
    a={n.name:ast.dump(n) for n in before.body if isinstance(n,ast.FunctionDef)}
    b={n.name:ast.dump(n) for n in after.body if isinstance(n,ast.FunctionDef)}
    assert a.keys()==b.keys()
    assert all(a[k]==b[k] for k in a if k!='classical')
    assert Path(base.__file__).read_bytes()==(ROOT/'runs/daytime-20260909/move-buffers-01/prototype/engine/compiled_core.py').read_bytes()
