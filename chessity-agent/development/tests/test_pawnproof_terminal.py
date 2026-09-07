"""The fast sufficient proof must agree with complete legal move generation."""

import random

import chess
import numpy as np
import pytest

from experiments import pawnproof_core as core
from experiments.compiled_driver import arrays


def compare(position):
    board, state = arrays(position)
    saved, ss = board.copy(), state.copy()
    expected = bool(position.legal_moves)
    assert bool(core.has_legal_move(board, state, position.is_check())) == expected, position.fen()
    assert bool(core.has_legal_move(board, state)) == expected
    assert np.array_equal(board, saved) and np.array_equal(state, ss)


def test_random_legal_play():
    rng = random.Random(2026090713)
    board = chess.Board()
    for _ in range(1500):
        if board.is_game_over() or board.ply() > 250:
            board = chess.Board()
        compare(board)
        board.push(rng.choice(list(board.legal_moves)))


@pytest.mark.parametrize('fen', [
    '7k/6Q1/5K2/8/8/8/8/8 b - - 0 1',
    '7k/5K2/6Q1/8/8/8/8/8 b - - 0 1',
    '8/8/8/r4pPK/8/8/8/4k3 w - f6 0 1',
    '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1',
    '4k3/P7/8/8/8/8/1p6/4K3 w - - 0 1',
    '4r1k1/8/8/8/8/8/4P3/4K3 w - - 0 1',
    '7k/8/8/8/7b/8/5P2/4K3 w - - 0 1',
    '7k/8/8/8/8/8/1P6/r3K3 w - - 0 1',
])
def test_terminal_check_pin_and_special_moves(fen):
    compare(chess.Board(fen))
    compare(chess.Board(fen).mirror())
