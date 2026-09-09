import ast
import importlib.util
import random
from pathlib import Path

import chess
import numpy as np
import pytest

from experiments import daytime_fast_legal_core as core
from scripts.daytime_common import RUN
from training.rule_value import arrays

FENS = [
    chess.STARTING_FEN,
    'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1',
    '7k/5Q2/6K1/8/8/8/8/8 b - - 0 1',
    '7k/6Q1/6K1/8/8/8/8/8 b - - 0 1',
    '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2',
    '4r1k1/8/8/8/8/8/4R3/4K3 w - - 0 1',
    '7k/P7/6K1/8/8/8/8/8 w - - 0 1',
    '7k/8/8/8/8/8/PP6/KR6 w - - 0 1',
]


@pytest.fixture(scope='module')
def original():
    spec = importlib.util.spec_from_file_location('fast_legal_exact55',
        RUN/'pawn-bitboards-01/prototype/engine/compiled_core.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def verify(board, original):
    assert board.is_valid()
    pieces, state = arrays(board)
    saved = pieces.copy(), state.copy()
    expected = any(board.legal_moves)
    assert bool(core.has_legal_move(pieces,state)) == expected
    assert np.array_equal(pieces,saved[0]) and np.array_equal(state,saved[1])
    assert bool(original.has_legal_move(pieces,state)) == expected
    assert np.array_equal(pieces,saved[0]) and np.array_equal(state,saved[1])


@pytest.mark.parametrize('fen', FENS)
def test_terminal_special_rules_and_state_restoration(fen,original):
    board = chess.Board(fen)
    verify(board,original)
    verify(board.mirror(),original)


def test_random_positions_and_mirrors(original):
    rng = random.Random(2026090913)
    board = chess.Board()
    for _ in range(600):
        verify(board,original)
        verify(board.mirror(),original)
        if board.is_game_over(claim_draw=True) or board.ply()>=180:
            board = chess.Board()
        else:
            board.push(rng.choice(list(board.legal_moves)))


def test_only_existence_helper_changed():
    before = ast.parse((RUN/'pawn-bitboards-01/prototype/engine/compiled_core.py').read_text())
    after = ast.parse(Path(core.__file__).read_text())
    a = {n.name:ast.dump(n) for n in before.body if isinstance(n,ast.FunctionDef)}
    b = {n.name:ast.dump(n) for n in after.body if isinstance(n,ast.FunctionDef)}
    assert a.keys()==b.keys()
    assert all(a[k]==b[k] for k in a if k!='has_legal_move')
