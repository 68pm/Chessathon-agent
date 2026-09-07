"""Differential legality, perft, evaluation parity and terminal behaviour."""

import random
import time

import chess
import numpy as np
import pytest

pytest.importorskip('numba')
from engine.evaluation import classical as reference_evaluation
from experiments import compiled_core as core
from experiments.compiled_driver import CompiledSearch, arrays, decode


@pytest.mark.parametrize('fen,depth,expected', [
    (chess.STARTING_FEN, 4, 197281),
    ('r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1', 3, 97862),
    ('8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1', 4, 43238),
])
def test_perft(fen, depth, expected):
    board, state = arrays(chess.Board(fen))
    saved, ss = board.copy(), state.copy()
    assert core.perft(board, state, depth) == expected
    assert np.array_equal(board, saved) and np.array_equal(state, ss)


def test_random_differential_legality_and_evaluation():
    rng = random.Random(2026090714)
    board = chess.Board()
    for _ in range(1800):
        if board.is_game_over() or board.ply() > 250:
            board = chess.Board()
        b, s = arrays(board)
        moves = core.legal_moves(b, s)
        assert {decode(int(m)) for m in moves} == set(board.legal_moves), board.fen()
        assert core.has_legal_move(b, s) == bool(board.legal_moves), board.fen()
        assert core.classical(b, s) == reference_evaluation(board), board.fen()
        assert bool(core.insufficient(b)) == board.is_insufficient_material(), board.fen()
        assert np.array_equal(b, arrays(board)[0])
        board.push(rng.choice(list(board.legal_moves)))


@pytest.mark.parametrize('fen', [
    '7k/6Q1/5K2/8/8/8/8/8 b - - 0 1',
    '7k/5K2/6Q1/8/8/8/8/8 b - - 0 1',
    '8/8/8/r4pPK/8/8/8/4k3 w - f6 0 1',
    '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1',
    '4k3/P7/8/8/8/8/1p6/4K3 w - - 0 1',
])
def test_early_legal_predicate_terminal_and_special_moves(fen):
    board = chess.Board(fen)
    b, s = arrays(board)
    before, state_before = b.copy(), s.copy()
    assert core.has_legal_move(b, s) == bool(board.legal_moves)
    assert np.array_equal(b, before) and np.array_equal(s, state_before)


def test_ep_repetition_key_and_pin():
    for fen in [
        '8/8/8/r4pPK/8/8/8/4k3 w - f6 0 1',
        '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1',
        'rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1',
    ]:
        board = chess.Board(fen)
        b, s = arrays(board)
        value = core.position_hash(b, s)
        board.ep_square = None
        b2, s2 = arrays(board)
        equal = value == core.position_hash(b2, s2)
        assert equal == (not chess.Board(fen).has_legal_en_passant())


@pytest.mark.parametrize('reductions', [False, True])
def test_search_mate_restoration_and_node_limit(reductions):
    search = CompiledSearch(reductions=reductions)
    search.warmup()
    board = chess.Board('7k/8/5KQ1/8/8/8/8/8 w - - 0 1')
    fen = board.fen()
    result = search.run(board, seconds=1, max_nodes=100000)
    board.push(result.move)
    assert board.is_checkmate()
    board.pop()
    assert board.fen() == fen
    result = search.run(chess.Board(), seconds=10, max_nodes=2048)
    assert result.nodes <= 2048 and result.move in chess.Board().legal_moves


def test_residual_used_by_leaf_evaluation():
    b, s = arrays(chess.Board())
    w = np.zeros((768, 32), dtype=np.float32)
    bias = np.ones(32, dtype=np.float32)
    out = np.ones(32, dtype=np.float32)
    assert core.evaluate(b, s, w, bias, out, 1.0, False) - core.classical(b, s) == 32
    assert core.evaluate(b, s, w, bias, out, 0.0, False) == core.classical(b, s)


def test_residual_gradients_and_runtime_parity():
    from training.residual_value import features, forward, gradients

    rng = np.random.default_rng(99)
    parameters = [rng.normal(0, 0.005, (768, 32)), np.full(32, 0.4), rng.normal(0, 0.1, 32)]
    board = chess.Board('r3k2r/ppp2ppp/2n5/3pp3/3PP3/2N5/PPP2PPP/R3K2R b KQkq - 0 1')
    x = np.array([features(board)])
    y = np.array([0.1])
    grads = gradients(x, y, parameters)
    for parameter, gradient, index in zip(parameters, grads, [(0, 0), (3,), (7,)]):
        before = parameter[index]
        epsilon = 1e-5
        parameter[index] = before + epsilon
        plus = 0.5 * np.sum((forward(x, parameters)[0] - y)**2)
        parameter[index] = before - epsilon
        minus = 0.5 * np.sum((forward(x, parameters)[0] - y)**2)
        parameter[index] = before
        assert abs((plus - minus) / (2 * epsilon) - gradient[index]) < 1e-6
    b, s = arrays(board)
    value = core.evaluate(b, s, parameters[0], parameters[1], parameters[2] * 200, 1.0, False)
    assert abs(value - core.classical(b, s) - float(forward(x, parameters)[0][0]) * 200) < 0.51


def test_completed_search_scores_match_preserved_algorithm():
    from engine.search import Search

    for fen in [chess.STARTING_FEN,
                '4k3/pp3ppp/2n5/3pp3/3PP3/2N5/PPP2PPP/4K3 w - - 0 15',
                '6k1/5ppp/8/8/8/8/5PPP/3R2K1 w - - 0 1']:
        board = chess.Board(fen)
        reference = Search().run(board, seconds=10, soft=10, max_depth=2)
        candidate = CompiledSearch().run(board, seconds=30, soft=30, max_depth=2)
        assert reference.depth == candidate.depth
        assert reference.depth == 2 or abs(reference.score) > 29900
        assert reference.score == candidate.score


def test_incremental_accumulators_restore_and_match_full_sum():
    rng = np.random.default_rng(19)
    w = rng.normal(0, 0.03, (768, 32)).astype(np.float32)
    bias = np.full(32, 0.3, dtype=np.float32)
    output = rng.normal(0, 20, 32).astype(np.float32)
    randomizer = random.Random(19)
    for fen in [chess.STARTING_FEN,
                'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1',
                '4k3/P7/8/8/8/8/1p6/4K3 w - - 0 1',
                '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1']:
        board = chess.Board(fen)
        b, s = arrays(board)
        accumulator = core.build_accumulator(b, w, bias)
        for move in core.legal_moves(b, s):
            saved = accumulator.copy()
            old = core.make(b, s, move)
            core.update_accumulator(accumulator, w, move, old, 1)
            assert np.allclose(accumulator, core.build_accumulator(b, w, bias), atol=1e-10)

            assert abs(core.evaluate_accumulator(b, s, output, 1.0, False, accumulator)
                       - core.evaluate(b, s, w, bias, output, 1.0, False)) <= 1
            core.update_accumulator(accumulator, w, move, old, -1)
            core.unmake(b, s, move, old)
            assert np.allclose(accumulator, saved, atol=1e-10)
        for _ in range(150):
            moves = core.legal_moves(b, s)
            if len(moves) == 0:
                break
            move = int(randomizer.choice(moves))
            old = core.make(b, s, move)
            core.update_accumulator(accumulator, w, move, old, 1)
            assert np.allclose(accumulator, core.build_accumulator(b, w, bias), atol=1e-10)


@pytest.mark.parametrize('wrong_context,wrong_clock,illegal_hint', [
    (True, False, False), (False, True, False), (True, True, False),
    (True, False, True), (False, False, False),
])
def test_transposition_hint_cannot_import_a_foreign_history_score(wrong_context, wrong_clock, illegal_hint):
    search = CompiledSearch()
    search.warmup()
    position = chess.Board('7k/8/5KQ1/8/8/8/8/8 w - - 8 1')
    board, state = arrays(position)
    saved, saved_state = board.copy(), state.copy()
    # Match root_iteration's uint64 context. A Python signed int would create a
    # different Numba signature with lossy mixed signed/unsigned comparisons.
    key = np.uint64(core.position_hash(board, state))
    hashes = np.zeros(800, dtype=np.uint64)
    hashes[0] = key
    slot = int(key) & (len(search.ttkey) - 1)
    search.ttkey[slot] = key
    search.ttcontext[slot] = np.uint64(int(key) ^ int(wrong_context))
    hint = 123456789 if illegal_hint else core.legal_moves(board, state)[-1]
    # Deliberately wrong exact score: a foreign context must not import it.
    search.ttdata[slot] = [20, 12345, 0, hint, state[3] + int(wrong_clock)]
    control = np.array([0, 0, 100000], dtype=np.int64)
    accumulator = core.build_accumulator(board, search.weights, search.bias)
    score = core.search(board, state, 2, -31000, 31000, 0, 0, hashes, 1, key,
                        search.ttkey, search.ttcontext, search.ttdata, search.killers,
                        search.history, control, time.perf_counter() + 30,
                        search.weights, search.bias, search.output, 0.0, False, False, accumulator)
    assert score == (29999 if wrong_context or wrong_clock else 12345)
    assert np.array_equal(board, saved) and np.array_equal(state, saved_state)
    assert control[1] == 0
