"""Compiled bitset queries and reversible state checked against independent chess rules."""

import ast
import importlib.util
import random

import chess
import numpy as np
import pytest

from experiments import overnight_bitsets_attacks as bits
from experiments import overnight_bitsets_core as core
from experiments.hash_driver import arrays as legacy_arrays
from experiments.hash_driver import decode
from scripts.overnight_bitsets import BASE, changed_source, specialize


def arrays(position):
    old, state = legacy_arrays(position)
    board = np.zeros(142, dtype=np.int64)
    board[:128] = old
    bits.rebuild_metadata(board)
    return board, state


def expected_metadata(position):
    masks = [0] * 14
    for square, piece in position.piece_map().items():
        signed_piece = piece.piece_type * (1 if piece.color else -1)
        masks[6 + signed_piece] |= 1 << square
        masks[13] |= 1 << square
    return np.asarray(masks, dtype=np.uint64).view(np.int64)


@pytest.fixture(scope='module')
def original():
    spec = importlib.util.spec_from_file_location('bitsets_original53', BASE / 'engine/compiled_core.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('value,expected', [(0, 64), (1, 63), (1 << 32, 31),
    (1 << 63, 0), ((1 << 64) - 1, 0)])
def test_native_leading_zero_semantics(value, expected):
    assert bits.count_leading_zeros(np.uint64(value)) == expected
    assert bits.count_leading_zeros.nopython_signatures


@pytest.mark.parametrize('operation', ['attacked', 'rebuild_metadata'])
def test_legacy_array_is_rejected(operation):
    board = np.zeros(128, dtype=np.int64)
    with pytest.raises(ValueError, match='142'):
        if operation == 'attacked':
            bits.attacked(board, 4, 1)
        else:
            bits.rebuild_metadata(board)


def test_high_bit_capture_replace_and_clear():
    position = chess.Board('7k/8/8/8/8/8/8/K7 w - - 0 1')
    board, _ = arrays(position)
    assert np.array_equal(board[128:], expected_metadata(position))
    assert board[141] < 0
    for signed_piece in [-5, 4, 0, -6]:
        bits.set_square(board, 119, signed_piece)
        piece = chess.Piece(abs(signed_piece), signed_piece > 0) if signed_piece else None
        position.set_piece_at(chess.H8, piece)
        assert np.array_equal(board[128:], expected_metadata(position))


SPECIAL_FENS = [
    'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1',
    '1r2k3/P7/8/8/8/8/1p6/4K3 w - - 0 1',
    '8/8/8/r4pPK/8/8/8/4k3 w - f6 0 1',
    '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1',
    'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
]


def verify_attacks(position):
    board, _ = arrays(position)
    assert np.array_equal(board[128:], expected_metadata(position))
    for square in chess.SQUARES:
        index = square // 8 * 16 + square % 8
        for color in (chess.WHITE, chess.BLACK):
            assert bits.attacked(board, index, 1 if color else -1) == position.is_attacked_by(color, square), (
                position.fen(), chess.square_name(square), color)


def verify_children(position, original):
    board, state = arrays(position)
    before, before_state = board.copy(), state.copy()
    moves = core.legal_moves(board, state)
    assert {decode(int(m)) for m in moves} == set(position.legal_moves)
    assert np.array_equal(board, before) and np.array_equal(state, before_state)
    assert core.position_hash(board, state) == original.position_hash(*legacy_arrays(position))
    assert np.array_equal(board, before) and np.array_equal(state, before_state)
    flags = set()
    for move in moves:
        old = core.make(board, state, move)
        child = position.copy(stack=True)
        child.push(decode(int(move)))
        expected_board, expected_state = legacy_arrays(child)
        assert np.array_equal(board[:128], expected_board)
        assert np.array_equal(board[128:], expected_metadata(child))
        assert np.array_equal(state, expected_state)
        child_before = board.copy()
        assert core.position_hash(board, state) == original.position_hash(expected_board, expected_state)
        assert np.array_equal(board, child_before) and np.array_equal(state, expected_state)
        flags.add((int(move) >> 17, (int(move) >> 14) & 7, bool(old[1])))
        core.unmake(board, state, move, old)
        assert np.array_equal(board, before) and np.array_equal(state, before_state)
    return len(moves), flags


def test_seeded_all_squares_and_all_legal_child_states(original):
    rng = random.Random(202609090034)
    position = chess.Board()
    total = 0
    for _ in range(240):
        if position.is_game_over(claim_draw=True) or position.ply() >= 180:
            position = chess.Board()
        verify_attacks(position)
        count, _ = verify_children(position, original)
        total += count
        position.push(rng.choice(list(position.legal_moves)))
    assert total > 3000
    print(f'Independent checks: 30,720 attack queries and {total} legal-child states/hashes.')


def test_special_moves_and_en_passant_hash_restoration(original):
    flags = set()
    for fen in SPECIAL_FENS:
        for position in [chess.Board(fen), chess.Board(fen).mirror()]:
            assert position.is_valid()
            verify_attacks(position)
            _, seen = verify_children(position, original)
            flags.update(seen)
            board, state = arrays(position)
            before = board.copy()
            key = core.position_hash(board, state)
            assert np.array_equal(board, before)
            no_ep = position.copy()
            no_ep.ep_square = None
            assert (key == core.position_hash(*arrays(no_ep))) == (not position.has_legal_en_passant())
    assert any(f & 2 for f, _, _ in flags)
    assert any(f & 1 for f, _, _ in flags)
    assert any(captured for _, _, captured in flags)
    assert {p for _, p, _ in flags if p} == {2, 3, 4, 5}


def test_long_make_unmake_stack_restores_every_metadata_slot():
    rng = random.Random(9060909)
    position = chess.Board()
    board, state = arrays(position)
    stack = []
    for _ in range(180):
        if position.is_game_over(claim_draw=True):
            break
        moves = core.legal_moves(board, state)
        move = rng.choice(list(moves))
        before, before_state = board.copy(), state.copy()
        old = core.make(board, state, move)
        stack.append((move, old, before, before_state))
        position.push(decode(int(move)))
        assert np.array_equal(board[128:], expected_metadata(position))
    assert len(stack) >= 60
    while stack:
        move, old, before, before_state = stack.pop()
        core.unmake(board, state, move, old)
        position.pop()
        assert np.array_equal(board, before) and np.array_equal(state, before_state)
        assert np.array_equal(board[128:], expected_metadata(position))


def test_starting_position_perft_four_and_restore():
    board, state = arrays(chess.Board())
    before, before_state = board.copy(), state.copy()
    assert core.perft(board, state, 3) == 8902
    assert core.perft(board, state, 4) == 197281
    assert np.array_equal(board, before) and np.array_equal(state, before_state)


def python_perft(board, depth):
    if not depth:
        return 1
    total = 0
    for move in list(board.legal_moves):
        board.push(move)
        total += python_perft(board, depth - 1)
        board.pop()
    return total


@pytest.mark.parametrize('fen', SPECIAL_FENS)
def test_special_position_perft_against_independent_rules(fen):
    position = chess.Board(fen)
    board, state = arrays(position)
    assert core.perft(board, state, 2) == python_perft(position, 2)


def test_only_declared_functions_change_after_classical_specialisation():
    original = (BASE / 'engine/compiled_core.py').read_text(encoding='utf-8')
    before = {n.name: ast.dump(n) for n in ast.parse(specialize(original)).body if isinstance(n, ast.FunctionDef)}
    after = {n.name: ast.dump(n) for n in ast.parse(changed_source(original)).body if isinstance(n, ast.FunctionDef)}
    for name in before.keys() - {'make', 'unmake', 'position_hash', 'attacked'}:
        assert before[name] == after[name], name
    assert before['attacked'].replace("name='attacked'", "name='attacked_scan'", 1) == after['attacked_scan']
