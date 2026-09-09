import ast
import importlib.util
import random

import chess
import numpy as np
import pytest

from experiments import overnight_pawn_masks_core as core
from experiments.hash_driver import arrays as legacy_arrays
from scripts.overnight_geometry_trial import BASE
from tests.test_overnight_bitsets_fixed import SPECIAL_FENS, arrays, decode


@pytest.fixture(scope='module')
def original():
    spec = importlib.util.spec_from_file_location('pawn_mask_original53', BASE / 'engine/compiled_core.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compare(position, original):
    board, state = arrays(position)
    old_board, old_state = legacy_arrays(position)
    before, before_state = board.copy(), state.copy()
    for conversion in (False, True):
        assert core.classical(board, state, conversion) == original.classical(old_board, old_state, conversion), position.fen()
    assert np.array_equal(board, before) and np.array_equal(state, before_state)


@pytest.mark.parametrize('count', [0, 1, 2, 3, 8])
def test_clamped_file_counts_including_high_bit(count):
    mask = np.uint64(sum(1 << (8 * rank + 7) for rank in range(8 - count, 8)))
    assert core.pawn_file_count(mask, 7) == min(count, 2)
    assert core.pawn_file_count(mask, 0) == 0


@pytest.mark.parametrize('fen', SPECIAL_FENS)
def test_special_positions_and_all_children_restore(fen, original):
    for position in (chess.Board(fen), chess.Board(fen).mirror()):
        compare(position, original)
        board, state = arrays(position)
        before, before_state = board.copy(), state.copy()
        for move in core.legal_moves(board, state):
            old = core.make(board, state, move)
            child = position.copy(stack=True)
            child.push(decode(int(move)))
            expected_board, expected_state = arrays(child)
            assert np.array_equal(board, expected_board) and np.array_equal(state, expected_state)
            for conversion in (False, True):
                assert core.classical(board, state, conversion) == original.classical(*legacy_arrays(child), conversion)
            core.unmake(board, state, move, old)
            assert np.array_equal(board, before) and np.array_equal(state, before_state)


def test_seeded_evaluation_parity_and_mirrors(original):
    rng = random.Random(202609090257)
    position = chess.Board()
    count = 0
    for _ in range(500):
        if position.is_game_over(claim_draw=True) or position.ply() >= 180:
            position = chess.Board()
        for board in (position, position.mirror()):
            compare(board, original)
            count += 2
        position.push(rng.choice(list(position.legal_moves)))
    assert core.classical.nopython_signatures
    print(f'Exact original evaluation parity for {count} seeded/mirrored conversion cases.')


def test_search_and_all_other_existing_functions_unchanged():
    from pathlib import Path

    from scripts.overnight_combined_search import BASE as CONTROL
    from scripts.overnight_combined_search import changed_source as combined
    before = {n.name: ast.dump(n) for n in ast.parse(combined((CONTROL / 'engine/compiled_core.py').read_text())).body if isinstance(n, ast.FunctionDef)}
    after = {n.name: ast.dump(n) for n in ast.parse(Path(core.__file__).read_text()).body if isinstance(n, ast.FunctionDef)}
    assert set(after) - set(before) == {'pawn_file_count'}
    assert all(before[name] == after[name] for name in before if name != 'classical')
