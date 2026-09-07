"""Independent legal-move oracle for the bounded material ordering heuristic."""

import random

import chess
import numpy as np
import pytest

from experiments import exchange_core as core
from experiments.compiled_driver import arrays, decode

VALUES = [0, 100, 325, 340, 505, 975, 30000]


def reference_reply(board, target, remaining=16):
    if not remaining or board.piece_type_at(target) == chess.KING:
        return 0
    moves = [m for m in board.legal_moves if m.to_square == target and board.is_capture(m)]
    if not moves:
        return 0
    # Match the documented 0x88 ascending-source / queen-first promotion tie rule,
    # independently of this engine's generator and legality implementation.
    move = min(moves, key=lambda m: (VALUES[board.piece_type_at(m.from_square)],
                                    m.from_square, -(m.promotion or 0)))
    gain = VALUES[board.piece_type_at(target)]
    if move.promotion:
        gain += VALUES[move.promotion] - VALUES[chess.PAWN]
    board.push(move)
    gain -= reference_reply(board, target, remaining - 1)
    board.pop()
    return max(0, gain)


def reference(board, move):
    gain = VALUES[chess.PAWN if board.is_en_passant(move) else board.piece_type_at(move.to_square) or 0]
    if move.promotion:
        gain += VALUES[move.promotion] - VALUES[chess.PAWN]
    board.push(move)
    value = 0 if board.is_check() else gain - reference_reply(board, move.to_square)
    board.pop()
    return value


def verify(board, uci=None, expected=None):
    b, s = arrays(board)
    saved_b, saved_s = b.copy(), s.copy()
    count = 0
    for move in core.legal_moves(b, s):
        decoded = decode(int(move))
        if uci and decoded.uci() != uci:
            continue
        if not board.is_capture(decoded) and not decoded.promotion:
            continue
        actual = core.capture_exchange(b, s, move)
        assert actual == reference(board, decoded), (board.fen(), decoded, actual)
        if expected is not None:
            assert actual == expected
        assert np.array_equal(b, saved_b) and np.array_equal(s, saved_s)
        count += 1
    return count


@pytest.mark.parametrize('fen,move,expected', [
    ('3r1k2/6pp/3pR3/1ppP1pPn/5P1P/2P1B3/2P2K2/8 w - - 1 37', 'e6d6', -405),
    ('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1', 'e5d6', 100),
    ('k7/8/2p5/3p4/4Q3/8/8/4K3 w - - 0 1', 'e4d5', -875),
    ('4k3/4r3/3p4/2Q5/8/8/8/4R1K1 w - - 0 1', 'c5d6', 100),
    ('7k/8/8/8/K7/8/1p6/2R5 b - - 0 1', 'b2c1q', 1380),
    ('7k/8/8/8/K7/8/1p6/2R5 b - - 0 1', 'b2c1n', 730),
    ('3k4/8/2p5/3p4/4Q3/8/8/4K3 w - - 0 1', 'e4d5', 0),
])
def test_directed_exchange_and_state(fen, move, expected):
    board = chess.Board(fen)
    assert board.is_valid()
    assert verify(board, move, expected) == 1


def test_random_capture_oracle():
    rng = random.Random(2026090709)
    board = chess.Board()
    checked = 0
    for _ in range(700):
        if board.is_game_over() or board.ply() > 150:
            board = chess.Board()
        checked += verify(board)
        board.push(rng.choice(list(board.legal_moves)))
    assert checked > 500


def test_ordering_keeps_all_moves_and_hint():
    board = chess.Board('3r1k2/6pp/3pR3/1ppP1pPn/5P1P/2P1B3/2P2K2/8 w - - 1 37')
    b, s = arrays(board)
    moves = core.legal_moves(b, s)
    original = moves.copy()
    indexed = {decode(int(m)).uci(): i for i, m in enumerate(moves)}
    killers, history = np.zeros((100, 2), dtype=np.int64), np.zeros((2, 128, 128), dtype=np.int64)
    bad, quiet = indexed['e6d6'], indexed['e3c1']
    shallow = core.order_moves(b, moves, 0, killers, history, 0, 1, s, 2)
    deep = core.order_moves(b, moves, 0, killers, history, 0, 1, s, 3)
    hinted = core.order_moves(b, moves, moves[bad], killers, history, 0, 1, s, 3)
    assert shallow[bad] > shallow[quiet] and deep[bad] < deep[quiet]
    assert hinted[bad] == 10000000 and np.array_equal(moves, original)
    assert np.array_equal(b, arrays(board)[0]) and np.array_equal(s, arrays(board)[1])


def test_search_mate_and_budget(monkeypatch):
    from experiments import compiled_driver

    monkeypatch.setattr(compiled_driver, 'core', core)
    search = compiled_driver.CompiledSearch()
    search.warmup()
    board = chess.Board('7k/8/5KQ1/8/8/8/8/8 w - - 0 1')
    original = board.fen()
    result = search.run(board, seconds=1, max_nodes=100000)
    assert board.fen() == original
    board.push(result.move)
    assert board.is_checkmate()
    board = chess.Board()
    result = search.run(board, seconds=10, max_nodes=10000)
    assert result.nodes <= 10000 and result.move in board.legal_moves
    assert board.fen() == chess.STARTING_FEN
