import ast
import random
from pathlib import Path

import chess
import numpy as np
import pytest

from experiments import daytime_contact_mate_core as core
from scripts.daytime_common import RUN
from scripts.daytime_tt_hint_test_call import call
from training.rule_value import arrays

FENS=[
    'r1bq1r2/1p1n1ppQ/p1n1p3/2bpP1N1/5Pk1/P1N5/1PP3PP/R1B1K2R w KQ - 6 14',
    'r1bq1r2/1p1n1ppQ/pbn1p3/3pP1N1/1P3Pk1/P1N5/2P3PP/R1B1K2R w KQ - 6 15',
]


def decode(move):
    a,b=move&127,(move>>7)&127
    return chess.Move((a//16)*8+a%16,(b//16)*8+b%16)


def oracle(board):
    enemy=board.king(not board.turn)
    rank=chess.square_rank(enemy)
    if (7-rank if board.turn else rank)<2:
        return set()
    mates=set()
    for move in board.legal_moves:
        if board.piece_type_at(move.from_square)!=chess.QUEEN or board.is_capture(move):
            continue
        if chess.square_distance(move.to_square,enemy)!=1:
            continue
        board.push(move)
        if board.is_checkmate():
            mates.add(move)
        board.pop()
    return mates


def verify(board):
    assert board.is_valid()
    pieces,state=arrays(board)
    saved=pieces.copy(),state.copy()
    history=list(board.move_stack)
    expected=oracle(board)
    move=core.quiet_contact_mate(pieces,state)
    assert bool(move)==bool(expected)
    if move:
        assert decode(int(move)) in expected
    assert np.array_equal(pieces,saved[0]) and np.array_equal(state,saved[1])
    assert board.move_stack==history


@pytest.mark.parametrize('fen',FENS)
@pytest.mark.parametrize('mirror',[False,True])
def test_actual_sacrificial_endpoints_are_mate_not_finite_training_targets(fen,mirror):
    board=chess.Board(fen)
    if mirror:
        board=board.mirror()
    verify(board)
    score,control,_=call(core,board,seed=False,depth=0)
    assert score==29999 and control[1]==0


@pytest.mark.parametrize('fen',[
    chess.STARTING_FEN,
    '7k/8/5KQ1/8/8/8/8/8 w - - 0 1',
    '4r1k1/8/8/8/8/8/4Q3/4K3 w - - 0 1',
    'r1b2rk1/1p3p2/p1np1qpp/4p3/2B1P3/P4N1P/1PPQ1PP1/R2R2K1 b - - 1 18',
])
def test_scope_pins_and_non_mates_against_independent_oracle(fen):
    board=chess.Board(fen)
    verify(board)
    verify(board.mirror())


def test_random_continuations_restore_state_and_never_invent_mate():
    rng=random.Random(2026090915)
    board=chess.Board(FENS[0])
    for i in range(240):
        verify(board)
        verify(board.mirror())
        if board.is_game_over() or i%12==11:
            board=chess.Board(rng.choice(FENS))
        else:
            board.push(rng.choice(list(board.legal_moves)))


def test_existing_functions_are_unchanged_except_leaf_mate_guard():
    before=ast.parse((RUN/'fast-legal-01/prototype/engine/compiled_core.py').read_text())
    after=ast.parse(Path(core.__file__).read_text())
    a={n.name:ast.dump(n) for n in before.body if isinstance(n,ast.FunctionDef)}
    b={n.name:ast.dump(n) for n in after.body if isinstance(n,ast.FunctionDef)}
    assert b.keys()-a.keys()=={'quiet_contact_mate'}
    assert all(a[k]==b[k] for k in a if k!='search')
