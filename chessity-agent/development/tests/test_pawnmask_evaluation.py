"""Geometric masks must match the existing forward-pawn definition exactly."""

import random

import chess
import numpy as np
import pytest

from engine.evaluation import classical as reference
from experiments import pawnmask_core as core
from experiments.compiled_driver import arrays


def compare(board):
    pieces, state = arrays(board)
    saved, ss = pieces.copy(), state.copy()
    assert core.classical(pieces, state) == reference(board), board.fen()
    assert np.array_equal(pieces, saved) and np.array_equal(state, ss)


def test_random_legal_play_parity():
    rng = random.Random(2026090712)
    board = chess.Board()
    for _ in range(1500):
        if board.is_game_over() or board.ply() > 250:
            board = chess.Board()
        compare(board)
        board.push(rng.choice(list(board.legal_moves)))


@pytest.mark.parametrize('fen', [
    '4k3/7p/8/8/8/8/P7/4K3 w - - 0 1',
    '4k3/8/p7/P7/7p/7P/8/4K3 b - - 0 1',
    '4k3/8/1p6/P7/8/8/8/4K3 w - - 0 1',
    '4k3/8/8/P7/1p6/8/8/4K3 b - - 0 1',
    '4k3/8/8/3P4/3Pp3/8/8/4K3 w - - 0 1',
    '4k3/1P6/8/8/8/8/6p1/4K3 b - - 0 1',
])
def test_edges_blockers_doubling_and_relative_rank(fen):
    board = chess.Board(fen)
    compare(board)
    compare(board.mirror())
