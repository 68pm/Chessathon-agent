"""New integration checks for the independently verified evaluator composition."""
import os

import chess
import numpy as np
import pytest

os.environ['NUMBA_DISABLE_ERROR_MESSAGE_HIGHLIGHTING'] = '1'

from experiments import queen_check_core as core  # noqa: E402
from experiments import queen_pawn_core as donor  # noqa: E402
from experiments.aspiration_driver import arrays  # noqa: E402


def search(board, module, depth=3, nodes=1000000):
    pieces, state = arrays(board)
    weights = np.zeros((768, 32), dtype=np.float32)
    bias = np.zeros(32, dtype=np.float32)
    accumulator = module.build_accumulator(pieces, weights, bias)
    replay, past = board.copy(stack=True), []
    for _ in range(min(board.halfmove_clock, len(board.move_stack)) + 1):
        p, s = arrays(replay)
        past.append(module.position_hash(p, s))
        if not replay.move_stack:
            break
        replay.pop()
    past.reverse()
    hashes = np.zeros(800, dtype=np.uint64)
    hashes[:len(past)] = past
    context = np.uint64(sum(map(int, past)) & ((1 << 64) - 1))
    control = np.array([0, 0, nodes], dtype=np.int64)
    saved = [p.copy() for p in [pieces, state, accumulator]]
    value = module.search(pieces, state, depth, -31000, 31000, 0, 0, hashes, len(past), context,
        np.zeros(4096, dtype=np.uint64), np.zeros(4096, dtype=np.uint64), np.zeros((4096, 5), dtype=np.int64),
        np.zeros((100, 2), dtype=np.int64), np.zeros((2, 128, 128), dtype=np.int64), control,
        float('inf'), weights, bias, bias, 0.0, False, False, accumulator, 2)
    assert all(np.array_equal(a, b) for a, b in zip(saved, [pieces, state, accumulator], strict=True))
    assert list(hashes[:len(past)]) == past
    return value, control


@pytest.mark.parametrize('fen', [
    '4b1Q1/8/5K2/8/prpk4/8/8/8 b - - 0 57',
    '4R3/5bP1/5K2/8/prpk4/8/8/8 b - - 15 56',
    '3R4/5pbk/8/5p2/P7/2N3P1/1qn1NP1P/6K1 w - - 1 40',
])
def test_accumulator_dispatch_uses_verified_contextual_evaluation(fen):
    board = chess.Board(fen)
    assert board.is_valid()
    pieces, state = arrays(board)
    before = pieces.copy(), state.copy()
    weights = np.zeros((768, 32), dtype=np.float32)
    bias = np.zeros(32, dtype=np.float32)
    accumulator = core.build_accumulator(pieces, weights, bias)
    expected = donor.classical(pieces, state, False)
    assert core.evaluate_accumulator(pieces, state, bias, 0.0, False, accumulator) == expected
    assert core.evaluate(pieces, state, weights, bias, bias, 0.0, False) == expected
    assert np.array_equal(pieces, before[0]) and np.array_equal(state, before[1])


@pytest.mark.parametrize('fen, expected', [
    ('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1', 0),
    ('7k/6Q1/5K2/8/8/8/8/8 b - - 100 1', -30000),
])
def test_terminal_priority_precedes_changed_evaluation(fen, expected):
    board = chess.Board(fen)
    assert board.is_valid()
    assert search(board, core)[0] == expected


def test_interruption_restores_real_position():
    board = chess.Board('3R4/5pbk/8/5p2/P7/2N3P1/1qn1NP1P/6K1 w - - 1 40')
    value, control = search(board, core, depth=6, nodes=512)
    assert value == 0 and control[1] and control[0] == 512
