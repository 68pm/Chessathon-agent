"""Static caching must preserve the evaluator and leave game state untouched."""

import random

import chess
import numpy as np
import pytest

from experiments import compiled_driver as driver
from experiments import evalcache_core as core


@pytest.mark.parametrize('blend', [0., .25, 1.])
def test_random_legal_positions_replacements_and_side_keys(blend):
    rng = random.Random(2026090711)
    np_rng = np.random.default_rng(11)
    weights = np_rng.normal(0, .03, (768, 32)).astype(np.float32)
    bias = np.full(32, .4, dtype=np.float32)
    output = np_rng.normal(0, 20, 32).astype(np.float32)
    keys = np.zeros(8, dtype=np.uint64)  # Deliberate frequent slot collisions.
    values = np.full(8, -2147483648, dtype=np.int64)
    position = chess.Board()
    for _ in range(400):
        if position.is_game_over() or position.ply() >= 200:
            position = chess.Board()
        board, state = driver.arrays(position)
        saved, ss = board.copy(), state.copy()
        accumulator = core.build_accumulator(board, weights, bias)
        key = np.uint64(core.position_hash(board, state))
        expected = core.evaluate_accumulator(board, state, output, blend, False, accumulator)
        for _ in range(2):
            assert core.cached_evaluate(board, state, key, output, blend, False,
                                        accumulator, keys, values) == expected
        assert np.array_equal(board, saved) and np.array_equal(state, ss)
        if blend:
            assert (values == -2147483648).all()
        position.push(rng.choice(list(position.legal_moves)))


def test_zero_key_cannot_hit_an_empty_cache():
    board, state = driver.arrays(chess.Board('7k/8/8/8/8/8/1Q6/K7 w - - 0 1'))
    keys = np.zeros(1, dtype=np.uint64)
    values = np.full(1, -2147483648, dtype=np.int64)
    expected = core.classical(board, state)
    assert expected != 0
    assert core.cached_evaluate(board, state, np.uint64(0), np.zeros(32), 0., False,
        np.zeros((2, 32)), keys, values) == expected


def test_package_driver_mate_draw_state_and_node_limit(monkeypatch):
    monkeypatch.setattr(driver, 'core', core)
    search = driver.CompiledSearch()
    search.warmup()
    board = chess.Board()
    result = search.run(board, 3, 3, max_nodes=100000)
    assert result.move in board.legal_moves and result.nodes <= 100000
    assert board.fen() == chess.STARTING_FEN
    mate = chess.Board('7k/8/5KQ1/8/8/8/8/8 w - - 0 1')
    result = search.run(mate, 1, 1)
    mate.push(result.move)
    assert mate.is_checkmate()
    stalemate = chess.Board('7k/5K2/6Q1/8/8/8/8/8 b - - 0 1')
    assert search.run(stalemate).move is None
