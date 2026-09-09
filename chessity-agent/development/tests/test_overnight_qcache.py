"""Independent cache algebra and search precedence tests without a second JIT job."""

import ast

import numpy as np
import pytest

from scripts.overnight_qcache import BASE, changed_source


def environment():
    source = changed_source((BASE / 'engine/compiled_core.py').read_text(encoding='utf-8'))
    wanted = {'search', 'qcache_context', 'qcache_store', 'qcache_probe'}
    nodes = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name in wanted]
    for node in nodes:
        node.decorator_list = []
    env = {'np': np}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), 'extracted-qcache-search', 'exec'), env)
    return env


def tables():
    return np.zeros(16, dtype=np.uint64), np.zeros(16, dtype=np.uint64), np.zeros((16, 5), dtype=np.int64)


@pytest.mark.parametrize('value,alpha,beta,query_alpha,query_beta,hit', [
    (42, -100, 100, -1, 1, True),       # exact works for any window
    (150, -100, 100, -100, 140, True),  # lower bound proves cutoff
    (150, -100, 100, -100, 160, False),
    (-150, -100, 100, -140, 100, True), # upper bound proves cutoff
    (-150, -100, 100, -160, 100, False),
    (100, -100, 100, -100, 101, False), # beta equality is a bound, not exact
    (-100, -100, 100, -101, 100, False),
])
def test_window_bounds_are_not_mistaken_for_exact_scores(value, alpha, beta, query_alpha, query_beta, hit):
    env, tt = environment(), tables()
    key, context = np.uint64(77), np.uint64(231)
    env['qcache_store'](key, context, 7, 3, value, 19, alpha, beta, *tt)
    found, answer = env['qcache_probe'](key, context, 7, 3, query_alpha, query_beta, *tt)
    assert found == hit
    assert answer == (value if hit else 0)


@pytest.mark.parametrize('value,expected', [(29990, 29995), (-29990, -29995), (430, 430)])
def test_mate_distance_is_relative_to_the_new_search_ply(value, expected):
    env, tt = environment(), tables()
    key, context = np.uint64(77), np.uint64(231)
    env['qcache_store'](key, context, 7, 7, value, 19, -31000, 31000, *tt)
    assert env['qcache_probe'](key, context, 7, 2, -31000, 31000, *tt) == (True, expected)


def test_normal_search_entries_are_not_replaced_and_key_collisions_are_misses():
    env, tt = environment(), tables()
    key, context = np.uint64(77), np.uint64(231)
    slot = int(key & np.uint64(15))
    tt[0][slot], tt[1][slot], tt[2][slot, 0] = key, context, 6
    before = [a.copy() for a in tt]
    env['qcache_store'](key + np.uint64(16), context, 7, 7, 40, 19, -100, 100, *tt)
    assert all(np.array_equal(a, b) for a, b in zip(tt, before, strict=True))
    assert env['qcache_probe'](key, context, 7, 7, -100, 100, *tt) == (False, 0)
    tt[2][slot, 0] = -1000
    assert env['qcache_probe'](key + np.uint64(16), context, 7, 7, -100, 100, *tt) == (False, 0)


def search_fixture():
    env, tt, calls = environment(), tables(), []
    env.update(attacked=lambda *args: False, insufficient=lambda *args: False,
        has_legal_move=lambda *args: True, clock_now=lambda: 0.)
    def evaluate(*args):
        calls.append(1)
        return 27
    env['evaluate_accumulator'] = evaluate
    def call(depth=0, qdepth=12, extensions=2, credits=4, attacker=0,
             context=59, clock=6, repetitions=1, max_nodes=100):
        board = np.zeros(128, dtype=np.int64)
        state = np.array([1, 0, -1, clock, 4, 116], dtype=np.int64)
        hashes = np.full(800, 77, dtype=np.uint64)
        original = board.copy(), state.copy(), hashes.copy()
        control = np.array([0, 0, max_nodes], dtype=np.int64)
        # Overflow is intentional modular hash arithmetic, as in the compiled engine.
        with np.errstate(over='ignore'):
            value = env['search'](board, state, depth, -100, 100, 1, qdepth,
                hashes, repetitions, np.uint64(context), *tt,
                np.zeros((100, 2), dtype=np.int64), np.zeros((2, 128, 128), dtype=np.int64),
                control, float('inf'), None, None, None, 0., False, False, None,
                extensions, credits, attacker)
        assert all(np.array_equal(a, b) for a, b in zip((board, state, hashes), original, strict=True))
        return value, control
    return env, tt, calls, call


def test_completed_leaf_is_reused_without_recomputing_evaluation():
    _, _, calls, call = search_fixture()
    assert call()[0] == call()[0] == 27
    assert len(calls) == 1


@pytest.mark.parametrize('change', [dict(depth=-1), dict(qdepth=13), dict(extensions=1),
    dict(credits=3), dict(attacker=1), dict(context=60), dict(clock=7)])
def test_every_search_horizon_and_history_component_separates_entries(change):
    _, _, calls, call = search_fixture()
    assert call()[0] == call(**change)[0] == 27
    assert len(calls) == 2


def test_repetition_draw_and_mate_precede_cache_reuse():
    env, _, calls, call = search_fixture()
    assert call()[0] == 27
    assert call(repetitions=3)[0] == 0
    assert len(calls) == 1
    env['attacked'] = lambda *args: True
    env['has_legal_move'] = lambda *args: False
    assert call(clock=100)[0] == -29999
    assert len(calls) == 1


def test_aborted_search_does_not_store_or_evaluate():
    _, tt, calls, call = search_fixture()
    score, control = call(max_nodes=1)
    assert score == 0 and control[1] == 1 and not calls
    assert all(np.count_nonzero(a) == 0 for a in tt)


def test_all_other53_engine_functions_and_constants_are_preserved():
    original = (BASE / 'engine/compiled_core.py').read_text(encoding='utf-8')
    changed = changed_source(original)
    allowed = {'search', 'qcache_context', 'qcache_store', 'qcache_probe'}
    def unchanged(text):
        return [ast.dump(n) for n in ast.parse(text).body
                if not (isinstance(n, ast.FunctionDef) and n.name in allowed)]
    assert unchanged(original) == unchanged(changed)
