"""Null search must not turn a virtual pass into game history or a legal move."""

import time

import chess
import numpy as np
import pytest

from experiments import compiled_driver as driver
from experiments import nullmove_core as core


@pytest.fixture
def search(monkeypatch):
    monkeypatch.setattr(driver, 'core', core)
    obj = driver.CompiledSearch()
    obj.warmup()
    return obj


def call(search, position, depth=4, alpha=-10001, beta=-10000, nodes=100000,
         repeat=False):
    board, state = driver.arrays(position)
    before, state_before = board.copy(), state.copy()
    key = np.uint64(core.position_hash(board, state))
    hashes = np.full(800, np.uint64(1234567))
    hlen = 3 if repeat else 1
    hashes[:hlen] = key
    accumulator = core.build_accumulator(board, search.weights, search.bias)
    saved_accumulator = accumulator.copy()
    control = np.array([0, 0, nodes, 0, 0, 0], dtype=np.int64)
    context = np.uint64(int(key) * hlen & ((1 << 64) - 1))
    score = core.search(board, state, depth, alpha, beta, 0, 0, hashes, hlen,
        context, search.ttkey, search.ttcontext, search.ttdata, search.killers,
        search.history, control, time.perf_counter() + 20,
        search.weights, search.bias, search.output, 0.0, False, False, accumulator,
        True, 0)
    assert np.array_equal(board, before)
    assert np.array_equal(state, state_before)
    assert np.array_equal(accumulator, saved_accumulator)
    assert all(hashes[i] == key for i in range(hlen))
    return score, control, hashes[hlen]


@pytest.mark.parametrize('fen,allowed', [
    (chess.STARTING_FEN, True),
    ('8/8/8/8/8/2k5/2p5/2K5 w - - 0 1', False),
    ('8/5k2/8/8/8/8/2K2r2/R7 w - - 0 1', False),
    ('4k3/8/8/8/8/8/8/1NB1K1bn w - - 0 1', False),
])
def test_material_guard_excludes_zugzwang_prone_endings(fen, allowed):
    board, _ = driver.arrays(chess.Board(fen))
    assert bool(core.null_material_ok(board)) == allowed


@pytest.mark.parametrize('nodes', [2, 100000])
def test_pass_restores_en_passant_clock_board_and_accumulator_even_on_abort(search, nodes):
    board = chess.Board()
    for move in ['e2e4', 'a7a6', 'e4e5', 'd7d5']:
        board.push_uci(move)
    assert board.has_legal_en_passant()
    _, control, next_hash = call(search, board, nodes=nodes)
    assert control[3] == 1
    assert bool(control[1]) == (nodes == 2)
    assert next_hash == 1234567
    assert control[0] <= nodes


def test_deep_cutoff_is_verified_on_original_position(search):
    _, control, _ = call(search, chess.Board(), depth=7)
    assert control[5] >= 1 and control[4] >= 1
    assert not control[1]


def test_real_threefold_draw_is_checked_before_null_probe(search):
    board = chess.Board()
    for move in ['g1f3', 'g8f6', 'f3g1', 'f6g8'] * 2:
        board.push_uci(move)
    assert board.is_repetition(3)
    score, control, _ = call(search, board, repeat=True)
    assert score == 0 and control[3] == 0


@pytest.mark.parametrize('fen,expected', [
    ('7k/6Q1/5K2/8/8/8/8/8 b - - 100 1', -30000),
    ('7k/5K2/6Q1/8/8/8/8/8 b - - 0 1', 0),
])
def test_mate_and_stalemate_are_not_null_cutoffs(search, fen, expected):
    score, control, _ = call(search, chess.Board(fen), alpha=-31000, beta=31000)
    assert score == expected and control[3] == 0


def test_completed_move_is_legal_and_budget_is_honoured(search):
    board = chess.Board()
    fen = board.fen()
    result = search.run(board, 3, 3, max_nodes=100000)
    assert result.move in board.legal_moves and result.nodes <= 100000
    assert board.fen() == fen
    mate = chess.Board('7k/8/5KQ1/8/8/8/8/8 w - - 0 1')
    result = search.run(mate, 1, 1)
    mate.push(result.move)
    assert mate.is_checkmate()
