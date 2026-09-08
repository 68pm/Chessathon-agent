"""Independent hash/state and fail-hard root oracle for the overnight integration."""
import ast
import random
import types
from pathlib import Path

import chess
import numpy as np
import pytest

from experiments import overnight_hash_scout_core_v2 as core
from experiments.hash_driver import arrays, decode


def verify_children(position):
    board, state = arrays(position)
    original, original_state = board.copy(), state.copy()
    parent = np.uint64(core.position_hash(board, state))
    parent_ep = core.ep_hash(board, state)
    count = 0
    flags = set()
    for move in core.legal_moves(board, state):
        old = core.make(board, state, move)
        child = core.hash_after_move(parent, parent_ep, board, state, move, old)
        assert child == core.position_hash(board, state)
        expected = position.copy(stack=True)
        expected.push(decode(int(move)))
        eb, es = arrays(expected)
        assert np.array_equal(board, eb) and np.array_equal(state, es)
        assert child == core.position_hash(eb, es)
        flags.add((int(move) >> 17, (int(move) >> 14) & 7, bool(old[1])))
        core.unmake(board, state, move, old)
        assert np.array_equal(board, original) and np.array_equal(state, original_state)
        assert core.position_hash(board, state) == parent
        count += 1
    return count, flags


def test_seeded_legal_children_match_full_recomputation():
    rng = random.Random(2026090718)
    position = chess.Board()
    total = 0
    for _ in range(240):
        if position.is_game_over(claim_draw=True) or position.ply() >= 180:
            position = chess.Board()
        count, _ = verify_children(position)
        total += count
        position.push(rng.choice(list(position.legal_moves)))
    assert total > 3000
    print(f'Checked {total} legal-child transitions across240 seeded positions.')


def test_castling_capture_promotions_and_ep_normalisation():
    fens = [
        'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1',
        '1r2k3/P7/8/8/8/8/1p6/4K3 w - - 0 1',
        '8/8/8/r4pPK/8/8/8/4k3 w - f6 0 1',
        '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1',
        'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
    ]
    flags, total = set(), 0
    for fen in fens:
        for position in [chess.Board(fen), chess.Board(fen).mirror()]:
            assert position.is_valid()
            count, seen = verify_children(position)
            total += count
            flags.update(seen)
            board, state = arrays(position)
            key = core.position_hash(board, state)
            no_ep = position.copy()
            no_ep.ep_square = None
            assert (key == core.position_hash(*arrays(no_ep))) == (not position.has_legal_en_passant())
    assert any(f & 2 for f, _, _ in flags)
    assert any(f & 1 for f, _, _ in flags)
    assert any(captured for _, _, captured in flags)
    assert {p for _, p, _ in flags if p} == {2, 3, 4, 5}
    print(f'Checked {total} special-position child transitions, both colours.')



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
        ep_hash=lambda *args: np.uint64(0),
        hash_after_move=lambda parent, ep, p, s, move, old: np.uint64(p[0]),
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
                if not (isinstance(n, ast.FunctionDef) and n.name in {'root_iteration', 'search', 'hash_after_move', 'ep_hash'})]
    assert unchanged(source) == unchanged(changed)
