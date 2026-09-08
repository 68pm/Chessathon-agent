"""Credit limits, TT correctness and zero-credit equivalence to the selected core."""
import os

import chess
import numpy as np
import pytest

os.environ['NUMBA_DISABLE_ERROR_MESSAGE_HIGHLIGHTING'] = '1'
from experiments import check_extensions_core as core
from experiments.aspiration_driver import arrays


def arguments(board, module, depth=2, nodes=1000000):
    assert board.is_valid()
    p, s = arrays(board)
    weights = np.zeros((768, 32), dtype=np.float32)
    bias, output = (np.zeros(32, dtype=np.float32), np.zeros(32, dtype=np.float32))
    hashes = np.zeros(800, dtype=np.uint64)
    replay, past = (board.copy(stack=True), [])
    for _ in range(min(board.halfmove_clock, len(board.move_stack)) + 1):
        b, state = arrays(replay)
        past.append(module.position_hash(b, state))
        if not replay.move_stack:
            break
        replay.pop()
    past.reverse()
    hashes[:len(past)] = past
    context = np.uint64(sum(map(int, past)) & (1 << 64) - 1)
    return [p, s, depth, -31000, 31000, 0, 0, hashes, len(past), context, np.zeros(4096, dtype=np.uint64), np.zeros(4096, dtype=np.uint64), np.zeros((4096, 5), dtype=np.int64), np.zeros((100, 2), dtype=np.int64), np.zeros((2, 128, 128), dtype=np.int64), np.array([0, 0, nodes], dtype=np.int64), float('inf'), weights, bias, output, 0.0, False, False, module.build_accumulator(p, weights, bias)]

def run(board, module=core, credits=2, depth=2, nodes=1000000):
    args = arguments(board, module, depth, nodes)
    before = [args[i].copy() for i in [0, 1, 7, 23]]
    value = module.search(*args, credits) if module is core else module.search(*args)
    assert np.array_equal(args[0], before[0]) and np.array_equal(args[1], before[1])
    assert np.array_equal(args[7][:args[8]], before[2][:args[8]]) and np.array_equal(args[23], before[3])
    return (value, args[15])

@pytest.mark.parametrize('credits', [1, 2])
def test_recursive_credit_budget_is_inherited_and_never_reset(monkeypatch, credits):
    original = core.search.py_func
    stack, seen = ([], [])

    def observed(*args):
        args = list(args)
        args[9] = np.uint64(int(args[9]) & (1 << 64) - 1)
        left = args[-1]
        assert 0 <= left <= credits
        if stack:
            expected = stack[-1]
            assert left == expected
        board, state, depth = args[:3]
        checked = core.attacked(board, state[4 if state[0] == 1 else 5], -state[0])
        next_left = left - int(checked and depth >= 0 and (left > 0))
        seen.append(left)
        stack.append(next_left)
        try:
            return original(*args)
        finally:
            stack.pop()
    monkeypatch.setattr(core, 'search', observed)
    board = chess.Board('8/6kp/6p1/1N6/P7/3BqnP1/2P2R1P/6K1 w - - 1 37')
    with np.errstate(over='ignore'):
        _, control = run(board, credits=credits, depth=1, nodes=512)
    assert len(seen) > 1 and min(seen) < credits and (control[0] <= 512)
