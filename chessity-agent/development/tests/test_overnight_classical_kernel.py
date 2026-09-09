"""Independent root-policy oracle and terminal checks for the specialised kernel."""

import ast

import numpy as np
import pytest

from scripts.overnight_classical_kernel import BASE, changed_source


def extract():
    source = changed_source((BASE / 'engine/compiled_core.py').read_text(encoding='utf-8'))
    nodes = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef)
             and n.name in ('search', 'root_iteration')]
    for node in nodes:
        node.decorator_list = []
    env = {'np': np}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'classical-kernel-oracle', 'exec'), env)
    return env


def root_trial(values, bonuses, interrupt=0, blend=0.):
    env, calls = extract(), []
    board, state = np.zeros(128, dtype=np.int64), np.array([1, 0, -1, 1, 4, 116])
    original = board.copy(), state.copy()
    control = np.array([0, 0, 10000], dtype=np.int64)
    def make(pieces, position, move):
        old = int(pieces[0]), 0, int(position[1])
        pieces[0] = move
        return old
    def unmake(pieces, position, move, old):
        pieces[0] = old[0]
    def child(*args):
        assert len(args) == 20 and args[-3:] == (False, False, 2)
        move, alpha, beta = int(args[0][0]), args[3], args[4]
        calls.append(move)
        if len(calls) == interrupt:
            control[1] = 1
            return 0
        return min(beta, max(alpha, -values[move - 1]))
    env.update(make=make, unmake=unmake, search=child,
        position_hash=lambda p, s: np.uint64(p[0]),
        order_moves=lambda *args: np.arange(len(values), 0, -1))
    result = env['root_iteration'](board, state, 4, 1, np.arange(1, len(values) + 1),
        np.asarray(bonuses), np.zeros(800, dtype=np.uint64), 1,
        None, None, None, None, None, control, float('inf'),
        object(), object(), object(), blend, False, False)
    assert np.array_equal(board, original[0]) and np.array_equal(state, original[1])
    return result, calls


@pytest.mark.parametrize('values,bonuses', [([20, 15, 10], [5, 25, 0]),
    ([30, 35, 20], [20, -10, 0]), ([60, 60, 60], [0, 0, 0]),
    ([29995, 29999, 25], [25, 5, 30]), ([-29998, -29995, -29997], [30, 20, -10]),
    ([10, 70, 0], [0, 0, 0])])
def test_active_policy_bonuses_and_mate_ordering_match_exhaustive_oracle(values, bonuses):
    result, _ = root_trial(values, bonuses)
    adjusted = [v + b if abs(v) < 29000 else v for v, b in zip(values, bonuses, strict=True)]
    best = max(adjusted)
    assert result == (adjusted.index(best) + 1, best, True)


@pytest.mark.parametrize('interrupt', [1, 2])
def test_root_interruption_restores_position_and_returns_previous(interrupt):
    result, calls = root_trial([10, 70, 0], [0, 0, 0], interrupt=interrupt)
    assert result == (1, 0, False) and len(calls) == interrupt


@pytest.mark.parametrize('blend', [.25, -1., float('nan')])
def test_nonzero_value_model_cannot_be_silently_ignored(blend):
    with pytest.raises(ValueError, match='zero leaf-value blend'):
        root_trial([10], [0], blend=blend)


def leaf_trial(repetitions=1, clock=6, checked=False, legal=True, max_nodes=100):
    env, calls = extract(), []
    def classical(board, state, conversion):
        calls.append(conversion)
        return 73
    env.update(classical=classical, attacked=lambda *args: checked,
        insufficient=lambda *args: False, has_legal_move=lambda *args: legal,
        clock_now=lambda: 0.)
    table = np.zeros((16, 5), dtype=np.int64)
    control = np.array([0, 0, max_nodes], dtype=np.int64)
    with np.errstate(over='ignore'):
        score = env['search'](np.zeros(128, dtype=np.int64), np.array([1, 0, -1, clock, 4, 116]),
            0, -100, 100, 1, 12, np.full(800, 77, dtype=np.uint64), repetitions, np.uint64(59),
            np.zeros(16, dtype=np.uint64), np.zeros(16, dtype=np.uint64), table,
            None, None, control, float('inf'), False, False, 2)
    return score, calls, control, table


def test_quiet_leaf_uses_identical_classical_score_and_terminal_precedence():
    assert leaf_trial()[0:2] == (73, [False])
    assert leaf_trial(repetitions=3)[0:2] == (0, [])
    assert leaf_trial(clock=100, checked=True, legal=False)[0:2] == (-29999, [])


def test_leaf_abort_does_not_evaluate_or_populate_the_table():
    score, calls, control, table = leaf_trial(max_nodes=1)
    assert score == 0 and control[1] == 1 and not calls and np.count_nonzero(table) == 0


def test_other53_rules_evaluation_and_move_ordering_functions_are_unchanged():
    original = (BASE / 'engine/compiled_core.py').read_text(encoding='utf-8')
    def other(text):
        return [ast.dump(n) for n in ast.parse(text).body
                if not (isinstance(n, ast.FunctionDef) and n.name in ('search', 'root_iteration'))]
    assert other(original) == other(changed_source(original))
