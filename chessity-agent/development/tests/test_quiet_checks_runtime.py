"""Quiet-leaf tactical reach, bounded expansion, terminal rules and restoration."""
import os
import time

import chess
import numpy as np
import pytest

os.environ['NUMBA_DISABLE_ERROR_MESSAGE_HIGHLIGHTING'] = '1'

from experiments import quiet_checks_core as core  # noqa: E402
from experiments.aspiration_driver import arrays  # noqa: E402


def qrun(board, qdepth=0, nodes=1000000):
    assert board.is_valid()
    pieces, state = arrays(board)
    saved_pieces, saved_state = pieces.copy(), state.copy()
    weights = np.zeros((768, 32), dtype=np.float32)
    bias = np.zeros(32, dtype=np.float32)
    output = np.zeros(32, dtype=np.float32)
    accumulator = core.build_accumulator(pieces, weights, bias)
    saved_accumulator = accumulator.copy()
    hashes = np.zeros(800, dtype=np.uint64)
    replay, past = board.copy(stack=True), []
    for _ in range(min(board.halfmove_clock, len(board.move_stack)) + 1):
        b, s = arrays(replay)
        past.append(core.position_hash(b, s))
        if not replay.move_stack:
            break
        replay.pop()
    past.reverse()
    hashes[:len(past)] = past
    context = np.uint64(sum(map(int, past)) & ((1 << 64) - 1))
    control = np.array([0, 0, nodes], dtype=np.int64)
    value = core.search(pieces, state, 0, -31000, 31000, 0, qdepth, hashes, len(past), context,
        np.zeros(4096, dtype=np.uint64), np.zeros(4096, dtype=np.uint64),
        np.zeros((4096, 5), dtype=np.int64), np.zeros((100, 2), dtype=np.int64),
        np.zeros((2, 128, 128), dtype=np.int64), control, float('inf'),
        weights, bias, output, 0.0, False, False, accumulator)
    assert np.array_equal(pieces, saved_pieces) and np.array_equal(state, saved_state)
    assert np.array_equal(accumulator, saved_accumulator) and list(hashes[:len(past)]) == past
    return value, control


@pytest.fixture(scope='module', autouse=True)
def compile_before_cases():
    started = time.perf_counter()
    qrun(chess.Board('7k/8/5KQ1/8/8/8/8/8 w - - 0 1'))
    assert time.perf_counter() - started < 180


def test_first_quiet_leaf_finds_non_capture_mate():
    board = chess.Board('7k/8/5KQ1/8/8/8/8/8 w - - 0 1')
    mates = []
    for move in board.legal_moves:
        child = board.copy()
        child.push(move)
        if child.is_checkmate():
            assert not board.is_capture(move)
            mates.append(move)
    assert mates
    score, control = qrun(board)
    assert score == 29999 and not control[1]


def test_quiet_checks_do_not_expand_past_first_leaf():
    score, control = qrun(chess.Board('7k/8/5KQ1/8/8/8/8/8 w - - 0 1'), qdepth=1)
    assert abs(score) < 29000 and control[0] == 1


def test_late_quiescence_retains_quiet_check_evasion():
    board = chess.Board('7k/8/6K1/8/8/8/8/7R b - - 0 1')
    assert board.is_check() and {m.uci() for m in board.legal_moves} == {'h8g8'}
    score, control = qrun(board, qdepth=12)
    assert abs(score) < 29000 and control[0] > 1 and not control[1]


@pytest.mark.parametrize('fen, expected', [
    ('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1', 0),
    ('7k/6Q1/5K2/8/8/8/8/8 b - - 100 1', -30000),
])
def test_terminal_rules_precede_quiet_search(fen, expected):
    board = chess.Board(fen)
    assert not any(board.legal_moves)
    assert qrun(board)[0] == expected


def test_non_capture_promotion_survives_quiet_check_budget():
    board = chess.Board('7k/5KP1/8/8/8/8/8/8 w - - 0 1')
    move = chess.Move.from_uci('g7g8q')
    assert move in board.legal_moves and not board.is_capture(move)
    child = board.copy()
    child.push(move)
    assert child.is_checkmate()
    assert qrun(board, qdepth=1)[0] == 29999


@pytest.mark.parametrize('fen', [
    '5k2/8/8/8/8/8/8/4K2R w K - 0 1',
    '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1',
    '7k/5KP1/8/8/8/8/8/8 w - - 0 1',
])
def test_interrupted_special_move_search_restores_state(fen):
    _, control = qrun(chess.Board(fen), nodes=2)
    assert control[1] and control[0] == 2


def test_repetition_history_still_draws():
    board = chess.Board()
    for move in ['g1f3', 'g8f6', 'f3g1', 'f6g8'] * 2:
        board.push_uci(move)
    assert board.is_repetition(3)
    assert qrun(board)[0] == 0
