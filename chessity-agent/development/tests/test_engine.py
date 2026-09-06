import time
from collections import Counter

import chess
import pytest

import agent
from engine.evaluation import classical
from engine.search import Search, position_key
from engine.time_manager import allocate
from engine.transposition import MATE, Table, pack_score, unpack_score


@pytest.mark.parametrize(
    "fen",
    [
        chess.STARTING_FEN,
        "r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1",
        "4k3/P7/8/8/8/8/7p/4K3 w - - 0 1",
        "4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1",
        "7k/8/5KQ1/8/8/8/8/8 w - - 0 1",
        "4k3/8/8/8/8/8/4r3/4K3 w - - 0 1",
    ],
)
def test_legal_and_restoration(fen):
    board = chess.Board(fen)
    result = Search().run(board, 0.03)
    assert result.move in board.legal_moves
    assert board.fen() == fen
    assert not board.move_stack
    assert chess.Move.from_uci(agent.get_move(fen, 15)) in board.legal_moves


def test_mate():
    b = chess.Board("7k/8/5KQ1/8/8/8/8/8 w - - 0 1")
    r = Search().run(b, 0.15)
    b.push(r.move)
    assert b.is_checkmate()
    assert r.score == MATE - 1


def test_draws():
    for fen in [
        "7k/5Q2/6K1/8/8/8/8/8 b - - 0 1",
        "7k/8/6K1/8/8/8/8/8 w - - 0 1",
        "7k/8/6K1/8/8/8/8/R7 w - - 100 1",
    ]:
        assert Search().run(chess.Board(fen), 0.02).score == 0
    b = chess.Board()
    assert Search().run(b, 0.02, known=Counter({position_key(b): 3})).score == 0


def test_qsearch_checkmate_before_fifty_move():
    b = chess.Board("7k/6Q1/6K1/8/8/8/8/8 b - - 100 1")
    r = Search().run(b, 0.02)
    assert r.move is None and r.score == -MATE


def test_symmetry():
    b = chess.Board()
    for move in ["e2e4", "c7c5", "g1f3", "b8c6", "f1b5"]:
        b.push_uci(move)
        assert classical(b) == classical(b.mirror())


def test_promotions():
    b = chess.Board("4k3/P7/8/8/8/8/8/4K3 w - - 0 1")
    assert {m.promotion for m in b.legal_moves if m.promotion} == {2, 3, 4, 5}
    for m in list(b.legal_moves):
        old = b.fen()
        b.push(m)
        assert b.is_valid()
        b.pop()
        assert b.fen() == old


def test_deadline_and_tt():
    b = chess.Board()
    start = time.monotonic()
    Search().run(b, 0.01)
    assert time.monotonic() - start < 0.15
    for score in [-29991, 29991, -130, 130]:
        assert unpack_score(pack_score(score, 7), 7) == score
    t = Table(16)
    for n in range(1000):
        t.put(n, 1, 2, 0, None)
    assert len(t.entries) == 16
    for ms in [0, 1, 10, 100, 1000, 120000]:
        budget = allocate(ms, 10, 30)
        assert 0 <= budget.soft <= budget.hard <= ms / 1000
