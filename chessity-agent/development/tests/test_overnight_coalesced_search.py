"""Root-value invariance and real compiler signature checks for boundary widening."""

import ast

import numpy as np
import pytest
from numba import njit, types

from scripts.overnight_coalesced_search import BASE, changed_source


@njit(cache=False)
def omitted(n, checks=4, attacker=0):
    if n:
        return omitted(n - 1, checks - int(n % 2 == 0), attacker if attacker else n)
    return checks + attacker


@njit(cache=False)
def widened(n, checks=4, attacker=0):
    if n:
        return widened(n - 1, checks - int(n % 2 == 0), attacker if attacker else n)
    return checks + attacker


@njit(cache=False)
def omitted_root(n):
    return omitted(n)


@njit(cache=False)
def widened_root(n):
    return widened(n, np.int64(4), np.int64(0))


def test_real_dynamic_recursion_has_one_generic_signature_and_same_value():
    for n in (0, 1, 2, 3, 11):
        assert omitted_root(n) == widened_root(n)
    assert len(omitted.signatures) > 1
    assert widened.signatures == [(types.int64, types.int64, types.int64)]
    print('Dynamic recursion diagnostic: omitted', len(omitted.signatures), 'widened', len(widened.signatures))


def root_trial(values, bonuses, interrupt=0):
    source = changed_source((BASE / 'engine/compiled_core.py').read_text(encoding='utf-8'))
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == 'root_iteration')
    node.decorator_list = []
    env = {'np': np}
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'explicit-root-oracle', 'exec'), env)
    board, state = np.zeros(128, dtype=np.int64), np.array([1, 0, -1, 1, 4, 116])
    before, before_state = board.copy(), state.copy()
    control, calls = np.asarray([0, 0, 10000]), []
    def make(pieces, position, move):
        old = int(pieces[0]), 0, int(position[1])
        pieces[0] = move
        return old
    def unmake(pieces, position, move, old):
        pieces[0] = old[0]
    def child(*args):
        assert len(args) == 27
        assert {i: int(args[i]) for i in (3, 5, 6, 24, 25, 26)} == {3: -31000, 5: 1, 6: 0, 24: 2, 25: 4, 26: 0}
        assert all(isinstance(args[i], np.int64) for i in (3, 5, 6, 24, 25, 26))
        move = int(args[0][0])
        calls.append(move)
        if len(calls) == interrupt:
            control[1] = 1
            return 0
        return min(args[4], max(args[3], -values[move - 1]))
    env.update(make=make, unmake=unmake, search=child,
        build_accumulator=lambda *args: None, position_hash=lambda p, s: np.uint64(p[0]),
        order_moves=lambda *args: np.arange(len(values), 0, -1))
    result = env['root_iteration'](board, state, 4, 1, np.arange(1, len(values) + 1),
        np.asarray(bonuses), np.zeros(800, dtype=np.uint64), 1,
        None, None, None, None, None, control, float('inf'),
        object(), object(), object(), 0., False, False)
    assert np.array_equal(board, before) and np.array_equal(state, before_state)
    return result, calls


@pytest.mark.parametrize('values,bonuses', [([20, 15, 10], [5, 25, 0]),
    ([30, 35, 20], [20, -10, 0]), ([60, 60, 60], [0, 0, 0]),
    ([29995, 29999, 25], [25, 5, 30]), ([-29998, -29995, -29997], [30, 20, -10]),
    ([10, 70, 0], [0, 0, 0]), ([-100, -90, -110], [-10, 15, 25])])
def test_policy_scores_and_mate_ordering_match_exhaustive_oracle(values, bonuses):
    result, _ = root_trial(values, bonuses)
    adjusted = [v + b if abs(v) < 29000 else v for v, b in zip(values, bonuses, strict=True)]
    best = max(adjusted)
    assert result == (adjusted.index(best) + 1, best, True)


@pytest.mark.parametrize('interrupt', [1, 2])
def test_abort_returns_previous_move_and_restores_board(interrupt):
    result, calls = root_trial([10, 70, 0], [0, 0, 0], interrupt)
    assert result == (1, 0, False) and len(calls) == interrupt


def test_only_root_call_boundary_changes_and_search_body_stays_identical():
    original = (BASE / 'engine/compiled_core.py').read_text(encoding='utf-8')
    before, after = ast.parse(original), ast.parse(changed_source(original))
    root = next(n for n in after.body if isinstance(n, ast.FunctionDef) and n.name == 'root_iteration')
    call = next(n for n in ast.walk(root) if isinstance(n, ast.Call)
                and isinstance(n.func, ast.Name) and n.func.id == 'search')
    for index in (3, 5, 6, 24):
        call.args[index] = call.args[index].args[0]
    del call.args[-2:]
    search = next(n for n in after.body if isinstance(n, ast.FunctionDef) and n.name == 'search')
    changed = 0
    for child in ast.walk(search):
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name) and child.func.id == 'search':
            if isinstance(child.args[6], ast.Call):
                assert ast.unparse(child.args[6]) == 'np.int64(0)'
                child.args[6] = child.args[6].args[0]
                changed += 1
    assert changed == 3
    assert ast.dump(before) == ast.dump(after)


@njit(cache=False)
def split_zero(n, qdepth):
    if n <= 0:
        return qdepth
    if n % 2:
        return split_zero(n - 1, 0)
    return split_zero(n - 1, qdepth + 1)


@njit(cache=False)
def wide_zero(n, qdepth):
    if n <= 0:
        return qdepth
    if n % 2:
        return wide_zero(n - 1, np.int64(0))
    return wide_zero(n - 1, qdepth + 1)


def test_recursive_literal_zero_coalesces_without_changing_values():
    for n in (0, 1, 2, 3, 12):
        assert split_zero(n, np.int64(0)) == wide_zero(n, np.int64(0))
    assert len(split_zero.signatures) > 1
    assert wide_zero.signatures == [(types.int64, types.int64)]
    print('Recursive zero diagnostic:', len(split_zero.signatures), 'to', len(wide_zero.signatures))
