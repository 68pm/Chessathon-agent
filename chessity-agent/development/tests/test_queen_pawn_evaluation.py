"""Verify the contextual correction against an independent board-level formula."""

import random

import chess
import numpy as np
import pytest

from engine.evaluation import classical as old_evaluation
from experiments import queen_pawn_core as core
from experiments.compiled_driver import arrays


def expected_delta(board):
    phase = sum(int(core.PHASE[p.piece_type]) for p in board.piece_map().values())
    if phase > 8:
        return 0
    white_delta = 0
    for colour in chess.COLORS:
        if board.pieces(chess.QUEEN, colour) or not board.pieces(chess.QUEEN, not colour):
            continue
        for sq in board.pieces(chess.PAWN, colour):
            file, rank = chess.square_file(sq), chess.square_rank(sq)
            relative_rank = rank if colour else 7 - rank
            blocked = any(abs(chess.square_file(p) - file) <= 1 and
                          (chess.square_rank(p) > rank if colour else chess.square_rank(p) < rank)
                          for p in board.pieces(chess.PAWN, not colour))
            if not blocked:
                white_delta -= (1 if colour else -1) * 3 * relative_rank**2
    return white_delta * (24 - phase) / 24 * (1 if board.turn else -1)


def verify(board):
    pieces, state = arrays(board)
    saved, ss = pieces.copy(), state.copy()
    actual, before = core.classical(pieces, state), old_evaluation(board)
    delta = expected_delta(board)
    assert abs(actual - before - delta) <= 1, board.fen()
    if delta == 0:
        assert actual == before
    mirrored, ms = arrays(board.mirror())
    assert core.classical(mirrored, ms) == actual
    assert np.array_equal(pieces, saved) and np.array_equal(state, ss)


def test_random_legal_scope_and_symmetry():
    rng = random.Random(2026090715)
    board = chess.Board()
    for _ in range(1000):
        if board.is_game_over() or board.ply() > 250:
            board = chess.Board()
        verify(board)
        board.push(rng.choice(list(board.legal_moves)))


@pytest.mark.parametrize('fen', [
    '4b1Q1/8/5K2/8/prpk4/8/8/8 b - - 0 57',
    '4R3/5bP1/5K2/8/prpk4/8/8/8 b - - 15 56',
    'q5k1/8/3p4/3P4/8/8/6K1/R7 w - - 0 1',
    'q5k1/8/3P4/3p4/8/8/6K1/R7 w - - 0 1',
    'q5k1/8/3P4/8/8/8/6K1/RQ6 w - - 0 1',
])
def test_specific_material_classes_and_blockers(fen):
    verify(chess.Board(fen))
