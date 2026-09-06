import random
import time
from collections import Counter

import chess
import pytest

from engine.advanced_search import Search, tactical_moves
from engine.search import Search as ReferenceSearch
from engine.search import position_key
from engine.transposition import MATE


def initialized(cls, board):
    search = cls()
    search.deadline = time.perf_counter() + 30
    search.nodes = 0
    search.counts = Counter()
    history = board.copy()
    while True:
        search.counts[position_key(history)] += 1
        if not history.move_stack:
            break
        history.pop()
    return search


def test_tactical_generation_matches_complete_legal_filter():
    rng = random.Random(9182)
    board = chess.Board()
    positions = [chess.Board(fen) for fen in [
        "4k3/P7/8/8/8/8/7p/4K3 w - - 0 1",
        "1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1",
        "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
        "8/k1P5/8/1K6/8/8/8/8 w - - 0 1",
    ]]
    for _ in range(200):
        if board.is_game_over() or board.ply() > 90:
            board = chess.Board()
        board.push(rng.choice(list(board.legal_moves)))
        positions.append(board.copy(stack=False))
    for board in positions:
        actual = tactical_moves(board)
        assert len(actual) == len(set(actual))
        assert set(actual) == {m for m in board.legal_moves if board.is_capture(m) or m.promotion}


@pytest.mark.parametrize("fen", [
    chess.STARTING_FEN,
    "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
    "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
    "8/k1P5/8/1K6/8/8/8/8 w - - 0 1",
    "7k/8/5KQ1/8/8/8/8/8 w - - 0 1",
    "4k3/8/8/8/8/8/4r3/4K3 w - - 0 1",
    "7k/6Q1/6K1/8/8/8/8/8 b - - 100 1",
    "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",
])
def test_pvs_agrees_with_full_window_reference(fen):
    board = chess.Board(fen)
    for depth in [0, 1, 2, 3]:
        reference = initialized(ReferenceSearch, board)
        candidate = initialized(Search, board)
        expected = reference.negamax(board, depth, -MATE - 1, MATE + 1, 0)
        actual = candidate.negamax(board, depth, -MATE - 1, MATE + 1, 0)
        assert actual == expected, (fen, depth, actual, expected)
        assert board.fen() == fen and not board.move_stack


def test_repetition_and_timeout_restore_full_history():
    board = chess.Board()
    for move in ["g1f3", "g8f6", "f3g1", "f6g8"] * 2:
        board.push_uci(move)
    search = initialized(Search, board)
    assert search.negamax(board, 3, -MATE - 1, MATE + 1, 0) == 0
    before = board.fen(), list(board.move_stack)
    search.run(board, seconds=1, max_nodes=50)
    assert (board.fen(), board.move_stack) == before
    fresh = chess.Board()
    result = Search().run(fresh, seconds=30, max_nodes=130)
    assert result.move in fresh.legal_moves and result.nodes <= 130
    assert fresh.fen() == chess.STARTING_FEN and not fresh.move_stack
