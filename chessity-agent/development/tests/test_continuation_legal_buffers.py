import ast
import random
from pathlib import Path

import chess
import numpy as np
import pytest

from experiments import continuation_legal_buffers_core as core
from scripts.continuation_common import ROOT
from training.rule_value import arrays


def check(board):
    pieces,state=arrays(board)
    saved=pieces.copy(),state.copy()
    storage=np.full((100,512),-37,dtype=np.int64)
    for ply in (0,96):
        answer=core.has_legal_move_buffered(pieces,state,storage[ply])
        assert answer==core.has_legal_move(pieces,state)==any(board.legal_moves)
        assert np.array_equal(pieces,saved[0]) and np.array_equal(state,saved[1])
        assert np.all(storage[1]==-37), 'Another ply was overwritten'
        a=core.generate(pieces,state,True)
        b=core.generate_buffered(pieces,state,True,storage[ply])
        assert np.array_equal(a,b)


@pytest.mark.parametrize('seed',range(8))
def test_legal_existence_and_storage_restore(seed):
    rng=random.Random(2026090940+seed)
    board=chess.Board()
    for _ in range(90):
        check(board)
        check(board.mirror())
        if board.is_game_over(claim_draw=True):board=chess.Board()
        else:board.push(rng.choice(list(board.legal_moves)))


def test_mates_stalemates_and_special_rules():
    for fen in ['7k/6Q1/6K1/8/8/8/8/8 b - - 0 1',
        '7k/5Q2/6K1/8/8/8/8/8 b - - 0 1',
        'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 99 50',
        '7k/8/8/3pP3/8/8/8/4K3 w - d6 0 1',
        '7k/P7/8/8/8/8/7p/4K3 w - - 0 1']:
        check(chess.Board(fen))


def test_undersized_storage_fails_before_board_mutation():
    pieces,state=arrays(chess.Board())
    saved=pieces.copy(),state.copy()
    with pytest.raises(AssertionError,match='Move storage exhausted'):
        core.has_legal_move_buffered(pieces,state,np.empty(1,dtype=np.int64))
    assert np.array_equal(pieces,saved[0]) and np.array_equal(state,saved[1])


def test_only_legal_buffer_helper_and_search_call_sites_change():
    before=ast.parse((ROOT/'runs/daytime-20260909/move-buffers-01/prototype/engine/compiled_core.py').read_text())
    after=ast.parse(Path(core.__file__).read_text())
    a={n.name:ast.dump(n) for n in before.body if isinstance(n,ast.FunctionDef)}
    b={n.name:ast.dump(n) for n in after.body if isinstance(n,ast.FunctionDef)}
    assert b.keys()-a.keys()=={'has_legal_move_buffered'}
    assert all(a[k]==b[k] for k in a if k!='search')
