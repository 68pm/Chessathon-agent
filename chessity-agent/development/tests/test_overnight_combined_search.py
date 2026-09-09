"""Run both compiled independent-rule suites against the actual combined core."""

import ast

import pytest

from experiments import overnight_combined_search_core as core
from scripts.overnight_combined_search import BASE, changed_source
from tests import test_overnight_bitsets_fixed as bit_suite
from tests import test_overnight_check_prefilter as check_suite


@pytest.fixture(autouse=True)
def use_combined_core(monkeypatch):
    monkeypatch.setattr(bit_suite, 'core', core)
    monkeypatch.setattr(check_suite, 'core', core)
    monkeypatch.setattr(check_suite, 'arrays', bit_suite.arrays)


original = bit_suite.original
test_native_leading_zero_semantics = bit_suite.test_native_leading_zero_semantics
test_legacy_array_is_rejected = bit_suite.test_legacy_array_is_rejected
test_high_bit_capture_replace_and_clear = bit_suite.test_high_bit_capture_replace_and_clear
test_seeded_all_squares_and_all_legal_child_states = bit_suite.test_seeded_all_squares_and_all_legal_child_states
test_special_moves_and_en_passant_hash_restoration = bit_suite.test_special_moves_and_en_passant_hash_restoration
test_long_make_unmake_stack_restores_every_metadata_slot = bit_suite.test_long_make_unmake_stack_restores_every_metadata_slot
test_starting_position_perft_four_and_restore = bit_suite.test_starting_position_perft_four_and_restore
test_special_position_perft_against_independent_rules = bit_suite.test_special_position_perft_against_independent_rules
test_special_and_discovered_checks_are_never_discarded = check_suite.test_special_and_discovered_checks_are_never_discarded
test_seeded_legal_moves_have_no_false_negative_checks_and_keep_state_pure = check_suite.test_seeded_legal_moves_have_no_false_negative_checks_and_keep_state_pure


def test_generated_core_and_all_explicit_search_arguments():
    expected = changed_source((BASE / 'engine/compiled_core.py').read_text(encoding='utf-8'))
    assert core.__file__
    from pathlib import Path
    assert Path(core.__file__).read_text(encoding='utf-8') == expected
    tree = ast.parse(expected)
    search = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'search')
    names = [n.arg for n in search.args.args]
    assert not {'weights', 'bias', 'output', 'blend', 'accumulator'} & set(names)
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == 'search']
    assert len(calls) == 5
    assert all(len(n.args) == len(names) for n in calls)
    assert expected.count('may_give_check(board, state, move)') == 2


def test_value_features_policy_and_time_manager_unchanged():
    from scripts.overnight_combined_search import OUT
    from scripts.overnight_geometry_trial import manifest
    before, after = manifest(BASE), manifest(OUT / 'prototype')
    changes = {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)}
    assert changes == {'engine/compiled_core.py', 'engine/compiled_driver.py', 'engine/overnight_bitsets_attacks_fixed.py'}
