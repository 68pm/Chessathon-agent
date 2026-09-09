import ast
import json
import random
from pathlib import Path

import chess
import numpy as np
import pytest

from experiments import daytime_move_buffers_core as core
from scripts.daytime_common import RUN
from training.rule_value import arrays


def check(board):
    pieces,state=arrays(board)
    saved=pieces.copy(),state.copy()
    moves_storage=np.full((2,512),-77,dtype=np.int64)
    score_storage=np.full((2,512),-88,dtype=np.int64)
    killers=np.zeros((100,2),dtype=np.int64)
    history=np.zeros((2,128,128),dtype=np.int64)
    for captures in (False,True):
        expected=core.generate(pieces,state,captures)
        actual=core.generate_buffered(pieces,state,captures,moves_storage[0])
        assert np.array_equal(actual,expected)
        assert len(actual)==0 or np.shares_memory(actual,moves_storage)
        if len(actual):
            killers[3,0]=actual[-1]
        a=core.order_moves(pieces,expected,0,killers,history,3,state[0])
        b=core.order_moves_buffered(pieces,actual,0,killers,history,3,state[0],score_storage[0])
        assert np.array_equal(a,b)
        before=actual.copy(),b.copy()
        core.generate_buffered(pieces,state,not captures,moves_storage[1])
        core.order_moves_buffered(pieces,expected,0,killers,history,3,state[0],score_storage[1])
        assert np.array_equal(actual,before[0]) and np.array_equal(b,before[1])
    assert np.array_equal(pieces,saved[0]) and np.array_equal(state,saved[1])


@pytest.mark.parametrize('seed',range(8))
def test_generated_ordering_and_separate_ply_storage_match(seed):
    rng=random.Random(2026090917+seed)
    board=chess.Board()
    for _ in range(110):
        check(board)
        check(board.mirror())
        if board.is_game_over(claim_draw=True):
            board=chess.Board()
        else:
            board.push(rng.choice(list(board.legal_moves)))


def test_special_moves_and_diagnosed_positions():
    roots=json.loads((RUN/'move-buffers-01/preparation.json').read_text())['roots']
    for fen in [r['fen'] for r in roots]+[
        'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1',
        '7k/P7/8/8/8/8/7p/4K3 w - - 0 1',
        '7k/8/8/3pP3/8/8/8/4K3 w - d6 0 1',
    ]:
        check(chess.Board(fen))


def test_small_storage_fails_safely_before_out_of_bounds_writes():
    pieces,state=arrays(chess.Board())
    saved=pieces.copy(),state.copy()
    with pytest.raises(AssertionError,match='Move storage exhausted'):
        core.generate_buffered(pieces,state,False,np.empty(1,dtype=np.int64))
    moves=core.generate(pieces,state)
    with pytest.raises(AssertionError,match='Score storage exhausted'):
        core.order_moves_buffered(pieces,moves,0,np.zeros((100,2),dtype=np.int64),
            np.zeros((2,128,128),dtype=np.int64),0,1,np.empty(1,dtype=np.int64))
    assert np.array_equal(pieces,saved[0]) and np.array_equal(state,saved[1])


def test_all_rule_evaluation_and_original_generator_functions_unchanged():
    before=ast.parse((RUN/'pawn-bitboards-01/prototype/engine/compiled_core.py').read_text())
    after=ast.parse(Path(core.__file__).read_text())
    a={n.name:ast.dump(n) for n in before.body if isinstance(n,ast.FunctionDef)}
    b={n.name:ast.dump(n) for n in after.body if isinstance(n,ast.FunctionDef)}
    assert b.keys()-a.keys()=={'generate_buffered','order_moves_buffered'}
    assert all(a[k]==b[k] for k in a if k not in ('search','root_iteration'))
