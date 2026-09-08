"""Independent fail-hard oracle for root windows; no second recursive JIT module."""
import ast
import types
from pathlib import Path

import numpy as np
import pytest

from experiments import competition_root_pvs_core as core


def exercise(values, bonuses, interrupt=0):
    calls, accumulators = [], []
    board, state = np.zeros(128, dtype=np.int64), np.array([1, 0, -1, 1, 0, 7])
    original = board.copy(), state.copy()
    control = np.array([0, 0, 10000], dtype=np.int64)
    moves = np.arange(1, len(values) + 1, dtype=np.int64)
    scores = dict(zip(map(int, moves), values, strict=True))

    def build(*unused):
        accumulator = np.zeros(32)
        accumulators.append(accumulator)
        return accumulator

    def make(pieces, position, move):
        old = int(pieces[0]), 0, int(position[1])
        pieces[0] = move
        return old

    def unmake(pieces, position, move, old):
        pieces[0] = old[0]

    def update(accumulator, weights, move, old, sign):
        accumulator[0] += sign * move

    def child(*args):
        alpha, beta = args[3:5]
        move = int(args[0][0])
        calls.append((move, int(alpha), int(beta)))
        if len(calls) == interrupt:
            control[1] = 1
            return 0
        # Fail-hard bounds deliberately hide the true score on a scout.
        return min(beta, max(alpha, -scores[move]))

    environment = dict(core.root_iteration.py_func.__globals__)
    environment.update(build_accumulator=build, make=make, unmake=unmake,
        update_accumulator=update, position_hash=lambda p, s: np.uint64(p[0]),
        order_moves=lambda *args: np.arange(len(values), 0, -1), search=child)
    function = types.FunctionType(core.root_iteration.py_func.__code__, environment)
    hashes = np.zeros(800, dtype=np.uint64)
    result = function(board, state, 4, 1, moves, np.array(bonuses, dtype=np.int64),
        hashes, 1, None, None, None, None, None, control, float('inf'), None,
        None, None, .25, False, False)
    assert np.array_equal(board, original[0]) and np.array_equal(state, original[1])
    assert len(accumulators) == 1 and np.count_nonzero(accumulators[0]) == 0
    return result, calls


@pytest.mark.parametrize('values,bonuses', [
    ([10, 70, 0], [0, 0, 0]),
    ([40, 35, 30], [0, 20, 0]),
    ([40, 55, 30], [10, -20, 0]),
    ([29995, 29999, 25], [25, 5, 30]),
    ([-29998, -29995, -29997], [30, 20, -10]),
    ([60, 60, 60], [0, 0, 0]),
])
def test_scout_matches_independent_exhaustive_oracle(values, bonuses):
    result, calls = exercise(values, bonuses)
    adjusted = [v + b if abs(v) < 29000 else v for v, b in zip(values, bonuses, strict=True)]
    best = max(adjusted)
    assert result == (adjusted.index(best) + 1, best, True)
    assert calls[0][1:] == (-31000, 31000)
    if values == [10, 70, 0]:
        assert calls[1:3] == [(2, -11, -10), (2, -31000, -10)]


@pytest.mark.parametrize('interrupt', [2, 3])
def test_interruption_in_scout_or_research_restores_and_returns_previous(interrupt):
    result, calls = exercise([10, 70, 0], [0, 0, 0], interrupt)
    assert result == (1, 0, False) and len(calls) == interrupt


def test_every_other_function_and_constant_is_identical_to_selected53():
    root = Path(__file__).resolve().parents[1]
    source = ast.parse((root / 'candidates/compiled-near-queen-checks-v1/engine/compiled_core.py').read_text())
    changed = ast.parse(Path(core.__file__).read_text())
    def unchanged(tree):
        return [ast.dump(n) for n in tree.body
                if not (isinstance(n, ast.FunctionDef) and n.name == 'root_iteration')]
    assert unchanged(source) == unchanged(changed)
