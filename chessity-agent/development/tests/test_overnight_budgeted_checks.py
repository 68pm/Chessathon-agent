"""Root budget and restoration oracle; recursive move search stays unchanged."""

import ast
import types
from pathlib import Path

import numpy as np
import pytest

from experiments import overnight_budgeted_checks_core as core


def exercise(depth, interrupt=0):
    pieces = np.zeros(128, dtype=np.int64)
    state = np.array([1, 0, -1, 0, 4, 116], dtype=np.int64)
    original = pieces.copy(), state.copy()
    controls = np.array([0, 0, 10000], dtype=np.int64)
    seen = []

    def make(board, position, move):
        old = int(board[0]), 0, int(position[1])
        board[0] = move
        return old

    def unmake(board, position, move, old):
        board[0] = old[0]

    def child(*args):
        seen.append(args[25])
        controls[0] += 1
        if controls[0] == interrupt:
            controls[1] = 1
            return 0
        value = -int(args[0][0]) * 10
        return min(args[4], max(args[3], value))

    environment = dict(core.root_iteration.py_func.__globals__)
    environment.update(make=make, unmake=unmake, search=child,
        build_accumulator=lambda *args: np.zeros(32),
        position_hash=lambda board, state: np.uint64(board[0]),
        order_moves=lambda *args: np.array([3, 2, 1]))
    root = types.FunctionType(core.root_iteration.py_func.__code__, environment)
    result = root(pieces, state, depth, 1, np.array([1, 2, 3]), np.zeros(3, dtype=np.int64),
        np.zeros(800, dtype=np.uint64), 1, None, None, None, None, None,
        controls, float('inf'), None, None, None, 0., False, False)
    assert np.array_equal(pieces, original[0]) and np.array_equal(state, original[1])
    return result, seen


@pytest.mark.parametrize('depth,credits', [(1, 2), (2, 2), (3, 4), (8, 4)])
def test_shallow_budget_and_full_deeper_search(depth, credits):
    result, seen = exercise(depth)
    assert result == (3, 30, True)
    assert seen == [credits] * 3


def test_interruption_returns_previous_after_restoring_board():
    result, seen = exercise(1, interrupt=2)
    assert result == (1, 0, False)
    assert seen == [2, 2]


def test_every_recursive_search_evaluation_and_draw_rule_is_unchanged():
    root = Path(__file__).resolve().parents[1]
    original = (root / 'candidates/compiled-near-queen-checks-v1/engine/compiled_core.py').read_text()
    changed = Path(core.__file__).read_text()
    def other_nodes(source):
        return [ast.dump(n) for n in ast.parse(source).body
                if not (isinstance(n, ast.FunctionDef) and n.name == 'root_iteration')]
    assert other_nodes(original) == other_nodes(changed)
