"""Quiet-leaf tactical reach, bounded expansion, terminal rules and restoration."""
import os

import chess
import numpy as np
import pytest

os.environ['NUMBA_DISABLE_ERROR_MESSAGE_HIGHLIGHTING'] = '1'
from experiments import quiet_checks_core as core
from experiments.aspiration_driver import arrays


def qrun(board, qdepth=0, nodes=1000000):
    assert board.is_valid()
    pieces, state = arrays(board)
    saved_pieces, saved_state = (pieces.copy(), state.copy())
    weights = np.zeros((768, 32), dtype=np.float32)
    bias = np.zeros(32, dtype=np.float32)
    output = np.zeros(32, dtype=np.float32)
    accumulator = core.build_accumulator(pieces, weights, bias)
    saved_accumulator = accumulator.copy()
    hashes = np.zeros(800, dtype=np.uint64)
    replay, past = (board.copy(stack=True), [])
    for _ in range(min(board.halfmove_clock, len(board.move_stack)) + 1):
        b, s = arrays(replay)
        past.append(core.position_hash(b, s))
        if not replay.move_stack:
            break
        replay.pop()
    past.reverse()
    hashes[:len(past)] = past
    context = np.uint64(sum(map(int, past)) & (1 << 64) - 1)
    control = np.array([0, 0, nodes], dtype=np.int64)
    value = core.search(pieces, state, 0, -31000, 31000, 0, qdepth, hashes, len(past), context, np.zeros(4096, dtype=np.uint64), np.zeros(4096, dtype=np.uint64), np.zeros((4096, 5), dtype=np.int64), np.zeros((100, 2), dtype=np.int64), np.zeros((2, 128, 128), dtype=np.int64), control, float('inf'), weights, bias, output, 0.0, False, False, accumulator)
    assert np.array_equal(pieces, saved_pieces) and np.array_equal(state, saved_state)
    assert np.array_equal(accumulator, saved_accumulator) and list(hashes[:len(past)]) == past
    return (value, control)

def test_non_capture_promotion_survives_quiet_check_budget():
    board = chess.Board('7k/5P2/6K1/8/8/8/8/8 w - - 0 1')
    move = chess.Move.from_uci('f7f8q')
    assert move in board.legal_moves and (not board.is_capture(move))
    child = board.copy()
    child.push(move)
    assert child.is_checkmate()
    assert qrun(board, qdepth=1)[0] == 29999

@pytest.mark.parametrize('fen', ['7k/5P2/6K1/8/8/8/8/8 w - - 0 1'])
def test_interrupted_special_move_search_restores_state(fen):
    _, control = qrun(chess.Board(fen), nodes=2)
    assert control[1] and control[0] == 2
