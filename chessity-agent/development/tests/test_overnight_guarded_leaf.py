import random

import chess
import numpy as np
import pytest

from experiments import overnight_guarded_leaf_core as core
from scripts.overnight_geometry_trial import ROOT
from tests.test_overnight_bitsets_fixed import SPECIAL_FENS, arrays as piece_arrays, decode
from training.rule_value import features


@pytest.fixture(scope='module')
def parameters():
    with np.load(ROOT / 'runs/overnight-20260909/rule-value-01/value.npz', allow_pickle=False) as data:
        return tuple(data[name].copy() for name in ('weights', 'rule_weights', 'bias', 'output'))


def arrays(board):
    pieces, state = piece_arrays(board)
    return pieces, np.append(state, np.int64(board.fullmove_number))


def oracle(board, parameters):
    weights, rules, bias, output = parameters
    x = features(board).astype(np.float64)
    hidden = x @ np.vstack((weights, rules)).astype(np.float64) + bias
    return float(np.clip(hidden, 0, 1) @ output.astype(np.float64))


def verify(position, parameters):
    weights, rules, bias, output = parameters
    board, state = arrays(position)
    before, before_state = board.copy(), state.copy()
    acc = core.build_accumulator(board, weights, bias)
    value = core.rule_residual(board, state, output, rules, acc)
    assert abs(value - oracle(position, parameters)) < .002
    assert core.legal_ep_file(board, state) == (chess.square_file(position.ep_square) if position.has_legal_en_passant() else -1)
    base, phase = core.classical_phase(board, state, False)
    expected = base if position.fullmove_number <= 12 or phase <= 8 else base + round(.5 * max(-600, min(600, value)))
    assert core.evaluate_accumulator(board, state, output, rules, .5, False, acc) == expected
    assert core.evaluate_accumulator(board, state, output, rules, 0., False, acc) == base
    assert np.array_equal(board, before) and np.array_equal(state, before_state)
    return board, state, acc


@pytest.mark.parametrize('fen', SPECIAL_FENS)
def test_special_moves_rules_and_incremental_restoration(fen, parameters):
    weights, rules, bias, output = parameters
    for position in (chess.Board(fen), chess.Board(fen).mirror()):
        position.fullmove_number = 20
        board, state, acc = verify(position, parameters)
        before, before_state, before_acc = board.copy(), state.copy(), acc.copy()
        for move in core.legal_moves(board, state):
            old = core.make(board, state, move)
            core.update_accumulator(acc, weights, move, old, 1)
            child = position.copy(stack=True)
            child.push(decode(int(move)))
            expected_board, expected_state = arrays(child)
            assert np.array_equal(board, expected_board) and np.array_equal(state, expected_state)
            assert np.allclose(acc, core.build_accumulator(board, weights, bias), atol=1e-10, rtol=0)
            assert abs(core.rule_residual(board, state, output, rules, acc) - oracle(child, parameters)) < .002
            core.update_accumulator(acc, weights, move, old, -1)
            core.unmake(board, state, move, old)
            assert np.array_equal(board, before) and np.array_equal(state, before_state)
            assert np.allclose(acc, before_acc, atol=1e-10, rtol=0)


@pytest.mark.parametrize('fullmove', [1, 12, 13, 40])
def test_opening_gate_and_draw_clock_are_exact(fullmove, parameters):
    position = chess.Board()
    position.fullmove_number = fullmove
    for clock in (0, 1, 69, 70, 99):
        position.halfmove_clock = clock
        verify(position, parameters)


def test_pawn_endings_stay_classical(parameters):
    for fen in ('8/7k/8/8/3P4/8/8/4K3 w - - 0 40',
                '4k3/8/8/8/3p4/8/7K/8 b - - 10 50'):
        position = chess.Board(fen)
        assert position.is_valid()
        board, state, acc = verify(position, parameters)
        assert core.evaluate_accumulator(board, state, parameters[3], parameters[1], .5, False, acc) == core.classical(board, state)


def test_seeded_histories_and_mirrors(parameters):
    rng = random.Random(202609090321)
    board = chess.Board()
    for _ in range(240):
        if board.is_game_over(claim_draw=True) or board.ply() >= 180:
            board = chess.Board()
        verify(board, parameters)
        verify(board.mirror(), parameters)
        board.push(rng.choice(list(board.legal_moves)))
    assert core.rule_residual.nopython_signatures
    print('480 seeded/mirrored positions matched the full 781-feature NumPy oracle.')


def test_fullmove_accumulator_long_stack_restores(parameters):
    weights, _, bias, _ = parameters
    position = chess.Board()
    board, state = arrays(position)
    acc = core.build_accumulator(board, weights, bias)
    rng = random.Random(202609090322)
    stack = []
    for _ in range(80):
        if position.is_game_over(claim_draw=True):
            break
        move = rng.choice(list(core.legal_moves(board, state)))
        stack.append((move, board.copy(), state.copy(), acc.copy()))
        old = core.make(board, state, move)
        stack[-1] += (old,)
        core.update_accumulator(acc, weights, move, old, 1)
        position.push(decode(int(move)))
        assert state[6] == position.fullmove_number
    assert len(stack) >= 40
    while stack:
        move, before, before_state, before_acc, old = stack.pop()
        core.update_accumulator(acc, weights, move, old, -1)
        core.unmake(board, state, move, old)
        assert np.array_equal(board, before) and np.array_equal(state, before_state)
        assert np.allclose(acc, before_acc, atol=1e-10, rtol=0)
