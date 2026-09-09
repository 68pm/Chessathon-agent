"""Independent full-hash oracle, special moves and unchanged-source checks for v1.42."""
import ast
import random
from pathlib import Path

import chess
import numpy as np
import pytest

from experiments import daytime_incremental_hash_core as core
from experiments.hash_driver import arrays, decode
from scripts.daytime_incremental_hash import transform


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



@pytest.mark.parametrize('fen', [
    'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1',
    '1r2k3/P7/8/8/8/8/1p6/4K3 w - - 0 1',
    '8/8/8/r4pPK/8/8/8/4k3 w - f6 0 1',
    '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1',
    chess.STARTING_FEN,
])
@pytest.mark.parametrize('mirror', [False, True])
def test_special_children_both_colours(fen, mirror):
    board = chess.Board(fen)
    assert verify_children(board.mirror() if mirror else board)[0] > 0


def test_only_declared_hash_updates_change_selected_source():
    root = Path(__file__).resolve().parents[1]
    old = (root / 'candidates/compiled-reductions-v1/engine/compiled_core.py').read_text()
    actual = Path(core.__file__).read_text()
    assert ast.dump(ast.parse(actual)) == ast.dump(ast.parse(transform(old)))
    assert 'childkey = position_hash(board, state)' not in actual
    assert '        key = position_hash(board, state)' not in actual
