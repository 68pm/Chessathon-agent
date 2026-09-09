import importlib.util
import random

import chess
import numpy as np
import pytest

from experiments import overnight_root_bootstrap_core as core
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


def search_arguments(board, state, **overrides):
    args = dict(board=board, state=state, depth=0, alpha=-31000, beta=31000,
        ply=1, qdepth=5, hashes=np.asarray([1234, 0], dtype=np.uint64), hlen=1,
        context=np.uint64(123), ttkey=np.zeros(16, dtype=np.uint64),
        ttcontext=np.zeros(16, dtype=np.uint64), ttdata=np.zeros((16, 5), dtype=np.int64),
        killers=np.zeros((100, 2), dtype=np.int64), history=np.zeros((2, 128, 128), dtype=np.int64),
        control=np.asarray([0, 0, 100000]), deadline=float('inf'),
        conversion=False, reductions=False, extensions_left=2, quiet_checks_left=4, quiet_attacker=-1)
    args.update(overrides)
    return args


@pytest.mark.parametrize('attacker,credits,expected_checks', [(-1, 4, True), (-1, 1, True),
    (-1, 0, False), (0, 4, False), (1, 4, True)])
def test_counterchecks_share_credits_and_exclude_nonchecks(monkeypatch, attacker, credits, expected_checks):
    position = chess.Board('6k1/8/8/1q6/8/8/8/3R2K1 w - - 0 20')
    assert position.is_valid() and not position.is_check()
    board, state = arrays(position)
    before, before_state = board.copy(), state.copy()
    expected = {}
    checks = 0
    for move in position.legal_moves:
        quiet = not position.is_capture(move) and not move.promotion
        checking = position.gives_check(move)
        if quiet and (not expected_checks or not checking):
            continue
        child = position.copy(stack=True)
        child.push(move)
        expected[tuple(arrays(child)[0])] = credits - int(quiet)
        checks += int(quiet and checking)
    assert bool(checks) == expected_checks
    visited = {}
    original = core.search.py_func

    def child(*args):
        visited[tuple(args[0])] = args[-2]
        assert args[-1] == attacker
        return 0

    monkeypatch.setattr(core, 'search', child)
    args = search_arguments(board, state, quiet_attacker=attacker, quiet_checks_left=credits)
    original(**args)
    assert visited == expected
    assert np.array_equal(board, before) and np.array_equal(state, before_state)
    assert args['control'][1] == 0


