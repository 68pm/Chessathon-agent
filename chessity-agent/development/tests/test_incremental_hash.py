"""Independent full-recomputation checks and real search guards for the new hash."""

import random
import time

import chess
import numpy as np
import pytest

from experiments import hash_core as core
from experiments.hash_driver import CompiledSearch, arrays, decode


def verify_children(position):
    board, state = arrays(position)
    original, original_state = board.copy(), state.copy()
    parent = np.uint64(core.position_hash(board, state))
    count = 0
    flags = set()
    for move in core.legal_moves(board, state):
        old = core.make(board, state, move)
        child = core.hash_after_move(parent, board, state, move, old)
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


@pytest.fixture(scope='module')
def searcher():
    search = CompiledSearch()
    search.warmup()
    return search


def test_mate_node_limit_and_board_restoration(searcher):
    board = chess.Board('7k/8/5KQ1/8/8/8/8/8 w - - 0 1')
    fen = board.fen()
    result = searcher.run(board, seconds=2, max_nodes=100000)
    assert board.fen() == fen
    board.push(result.move)
    assert board.is_checkmate()
    start = chess.Board()
    result = searcher.run(start, seconds=20, max_nodes=2048)
    assert result.nodes == 2048 and result.move in start.legal_moves
    assert start.fen() == chess.STARTING_FEN


@pytest.mark.parametrize('wrong_context,wrong_clock', [(True, False), (False, True), (False, False)])
def test_history_and_clock_still_guard_transposition_scores(searcher, wrong_context, wrong_clock):
    board, state = arrays(chess.Board('7k/8/5KQ1/8/8/8/8/8 w - - 8 1'))
    before, before_state = board.copy(), state.copy()
    key = np.uint64(core.position_hash(board, state))
    hashes = np.zeros(800, dtype=np.uint64)
    hashes[0] = key
    searcher.ttkey.fill(0)
    slot = int(key) & (len(searcher.ttkey) - 1)
    searcher.ttkey[slot] = key
    searcher.ttcontext[slot] = np.uint64(int(key) ^ int(wrong_context))
    searcher.ttdata[slot] = [20, 12345, 0, 0, state[3] + int(wrong_clock)]
    control = np.array([0, 0, 100000], dtype=np.int64)
    accumulator = core.build_accumulator(board, searcher.weights, searcher.bias)
    score = core.search(board, state, 2, -31000, 31000, 0, 0, hashes, 1, key,
        searcher.ttkey, searcher.ttcontext, searcher.ttdata, searcher.killers, searcher.history,
        control, time.perf_counter() + 20, searcher.weights, searcher.bias, searcher.output,
        0., False, False, accumulator)
    assert score == (29999 if wrong_context or wrong_clock else 12345)
    assert control[1] == 0
    assert np.array_equal(board, before) and np.array_equal(state, before_state)
