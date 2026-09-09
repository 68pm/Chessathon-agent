"""Independent legal-recapture and move-retention checks for bounded ordering."""
import ast
import random
from pathlib import Path

import chess
import numpy as np
import pytest

from experiments import evening_deep_exchange_core as core
from experiments.hash_driver import arrays, decode
from scripts.evening_deep_exchange_transform import transform


def encode(board, state, uci):
    return next(m for m in core.legal_moves(board, state) if decode(int(m)).uci() == uci)


def optional_recapture(position, target, limit=8):
    if not limit:
        raise AssertionError('Curated oracle exceeded its independent bound')
    gains = [0]
    for move in position.legal_moves:
        if move.to_square != target or not position.is_capture(move):
            continue
        captured = position.piece_type_at(target)
        value = int(core.MG[captured])
        if move.promotion:
            value += int(core.MG[move.promotion] - core.MG[chess.PAWN])
        position.push(move)
        gains.append(value - optional_recapture(position, target, limit - 1))
        position.pop()
    return max(gains)


CASES = [
    ('6k1/5ppp/2p5/3p4/8/8/3Q4/6K1 w - - 0 1', 'd2d5'),
    ('6k1/5ppp/2p5/3q4/8/8/3R4/6K1 w - - 0 1', 'd2d5'),
    ('6k1/5ppp/8/3p4/8/8/3Q4/6K1 w - - 0 1', 'd2d5'),
    ('4k3/4n3/8/3p4/2B5/8/4R3/6K1 w - - 0 1', 'c4d5'),
    ('8/8/4k3/3p4/8/8/3R4/6KB w - - 0 1', 'd2d5'),
]


@pytest.mark.parametrize('fen,uci', CASES)
@pytest.mark.parametrize('mirror', [False, True])
def test_small_exchanges_match_independent_legal_oracle_and_restore(fen, uci, mirror):
    position = chess.Board(fen)
    move = chess.Move.from_uci(uci)
    if mirror:
        position = position.mirror()
        move = chess.Move(chess.square_mirror(move.from_square), chess.square_mirror(move.to_square))
    assert position.is_valid() and move in position.legal_moves and not position.gives_check(move)
    board, state = arrays(position)
    before = board.copy(), state.copy()
    encoded = encode(board, state, move.uci())
    expected = int(core.MG[position.piece_type_at(move.to_square)])
    position.push(move)
    expected -= optional_recapture(position, move.to_square)
    position.pop()
    assert core.bounded_exchange(board, state, encoded) == expected
    assert np.array_equal(board, before[0]) and np.array_equal(state, before[1])


@pytest.mark.parametrize('fen,uci', [
    ('4k3/5p2/8/7Q/8/8/8/6K1 w - - 0 1', 'h5f7'),
    ('1r2k3/P7/8/8/8/8/8/4K3 w - - 0 1', 'a7b8q'),
    ('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1', 'e5d6'),
])
def test_checks_promotions_and_ep_keep_original_priority(fen, uci):
    position = chess.Board(fen)
    assert position.is_valid()
    board, state = arrays(position)
    before = board.copy(), state.copy()
    move = encode(board, state, uci)
    assert core.bounded_exchange(board, state, move) == 0
    assert np.array_equal(board, before[0]) and np.array_equal(state, before[1])


def test_ordering_demotes_bad_capture_retains_every_legal_move_and_hint():
    position = chess.Board(CASES[0][0])
    board, state = arrays(position)
    moves = core.legal_moves(board, state)
    before = board.copy(), state.copy(), moves.copy()
    killers, history = np.zeros((100, 2), dtype=np.int64), np.zeros((2, 128, 128), dtype=np.int64)
    bad = encode(board, state, 'd2d5')
    scores = core.order_moves(board, moves, 0, killers, history, 0, state[0], state, True)
    idx = next(i for i, move in enumerate(moves) if move == bad)
    assert scores[idx] < 0
    assert any(score >= 0 for score in scores)
    assert np.array_equal(moves, before[2]) and len(scores) == len(moves)
    assert core.order_moves(board, moves, bad, killers, history, 0, state[0], state, True)[idx] == 10000000
    assert np.array_equal(board, before[0]) and np.array_equal(state, before[1])


def test_seeded_ordering_restores_state_and_preserves_legal_moves():
    rng, position = random.Random(2026090902), chess.Board()
    killers, history = np.zeros((100, 2), dtype=np.int64), np.zeros((2, 128, 128), dtype=np.int64)
    for _ in range(150):
        if position.is_game_over():
            position = chess.Board()
        board, state = arrays(position)
        moves = core.legal_moves(board, state)
        before = board.copy(), state.copy(), moves.copy()
        scores = core.order_moves(board, moves, 0, killers, history, 0, state[0], state, True)
        assert len(scores) == len(moves) and np.array_equal(moves, before[2])
        assert np.array_equal(board, before[0]) and np.array_equal(state, before[1])
        assert {decode(int(m)) for m in moves} == set(position.legal_moves)
        position.push(rng.choice(list(position.legal_moves)))


def test_exact_declared_source_change():
    root = Path(__file__).resolve().parents[1]
    parent = (root / 'runs/daytime-20260909/move-buffers-01/prototype/engine/compiled_core.py').read_text()
    assert ast.dump(ast.parse(Path(core.__file__).read_text())) == ast.dump(ast.parse(transform(parent)))


def test_buffered_ordering_matches_plain_at_deep_ply():
    position=chess.Board(CASES[0][0]);board,state=arrays(position)
    moves=core.legal_moves(board,state);before=board.copy(),state.copy(),moves.copy()
    killers=np.zeros((100,2),dtype=np.int64);history=np.zeros((2,128,128),dtype=np.int64)
    storage=np.full((100,512),-37,dtype=np.int64)
    for enabled in (False,True):
        plain=core.order_moves(board,moves,0,killers,history,7,state[0],state,enabled)
        buffered=core.order_moves_buffered(board,moves,0,killers,history,7,state[0],storage[7],state,enabled)
        assert np.array_equal(plain,buffered) and np.all(storage[6]==-37)
    assert np.array_equal(board,before[0]) and np.array_equal(state,before[1]) and np.array_equal(moves,before[2])
