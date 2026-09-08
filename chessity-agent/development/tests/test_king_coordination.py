"""Independent attack-set oracle and state checks for cycle29."""
import json
import os
import random
from pathlib import Path

import chess
import numpy as np
import pytest

os.environ['NUMBA_DISABLE_ERROR_MESSAGE_HIGHLIGHTING'] = '1'

from experiments import king_coordination_core as core  # noqa: E402
from experiments import queen_check_core as parent  # noqa: E402
from experiments.aspiration_driver import arrays  # noqa: E402


def oracle(board):
    score = 0
    for side in [chess.WHITE, chess.BLACK]:
        if not board.pieces(chess.QUEEN, side):
            continue
        ring = chess.SquareSet(chess.BB_KING_ATTACKS[board.king(not side)])
        attackers, units = 0, 0
        for kind, weight in [(chess.KNIGHT, 2), (chess.BISHOP, 2), (chess.ROOK, 3), (chess.QUEEN, 5)]:
            for square in board.pieces(kind, side):
                hits = len(board.attacks(square) & ring)
                if hits:
                    attackers += 1
                    units += hits * weight
        if attackers >= 2:
            score += (1 if side else -1) * min(250, 2 * units ** 2)
    return score * (1 if board.turn else -1)


def positions(count):
    rng, board = random.Random(2026090829), chess.Board()
    for _ in range(count):
        for _ in range(3):
            if board.is_game_over() or board.ply() >= 160:
                board = chess.Board()
            board.push(rng.choice(list(board.legal_moves)))
        yield board.copy(stack=True)


def check_delta(board):
    assert board.is_valid()
    pieces, state = arrays(board)
    saved = pieces.copy(), state.copy()
    for conversion in [False, True]:
        assert core.classical(pieces, state, conversion) - parent.classical.py_func(pieces, state, conversion) == oracle(board)
    assert np.array_equal(pieces, saved[0]) and np.array_equal(state, saved[1])


def test_random_positions_match_independent_attack_sets():
    values = []
    for board in positions(160):
        check_delta(board)
        values.append(oracle(board))
    assert any(value != 0 for value in values) and 0 in values


def test_existing_refutation_positions_match_oracle():
    data = json.loads(Path('runs/improvement-loop-20260907/cycle-28/refutation-features.json').read_text())
    count = 0
    for line in data['lines']:
        for record in line['positions']:
            check_delta(chess.Board(record['fen']))
            count += 1
    assert count == 144


def test_color_mirror_preserves_side_to_move_evaluation():
    for board in positions(40):
        mirror = board.mirror()
        a, b = arrays(board), arrays(mirror)
        assert oracle(board) == oracle(mirror)
        assert core.classical(*a, False) == core.classical(*b, False)


def test_coordinated_attack_reaches_fixed_cap():
    board = chess.Board('R5k1/8/6Q1/8/8/8/8/K7 b - - 0 1')
    assert oracle(board) == -250
    check_delta(board)


@pytest.mark.parametrize('fen', [
    'R5k1/8/6R1/8/8/8/8/K7 b - - 0 1',
    '6k1/8/6Q1/8/8/8/8/K7 b - - 0 1',
])
def test_queenless_or_lone_queen_adds_nothing(fen):
    board = chess.Board(fen)
    assert oracle(board) == 0
    check_delta(board)


def search(board, module, depth=3, nodes=1000000):
    pieces, state = arrays(board)
    weights = np.zeros((768, 32), dtype=np.float32)
    bias = np.zeros(32, dtype=np.float32)
    accumulator = module.build_accumulator(pieces, weights, bias)
    replay, past = board.copy(stack=True), []
    for _ in range(min(board.halfmove_clock, len(board.move_stack)) + 1):
        p, s = arrays(replay)
        past.append(module.position_hash(p, s))
        if not replay.move_stack:
            break
        replay.pop()
    past.reverse()
    hashes = np.zeros(800, dtype=np.uint64)
    hashes[:len(past)] = past
    context = np.uint64(sum(map(int, past)) & ((1 << 64) - 1))
    control = np.array([0, 0, nodes], dtype=np.int64)
    saved = [p.copy() for p in [pieces, state, accumulator]]
    value = module.search(pieces, state, depth, -31000, 31000, 0, 0, hashes, len(past), context,
        np.zeros(4096, dtype=np.uint64), np.zeros(4096, dtype=np.uint64), np.zeros((4096, 5), dtype=np.int64),
        np.zeros((100, 2), dtype=np.int64), np.zeros((2, 128, 128), dtype=np.int64), control,
        float('inf'), weights, bias, bias, 0.0, False, False, accumulator, 2)
    assert all(np.array_equal(a, b) for a, b in zip(saved, [pieces, state, accumulator], strict=True))
    assert list(hashes[:len(past)]) == past
    return value, control


def test_terminal_priority_before_new_value():
    for fen, expected in [
        ('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1', 0),
        ('7k/6Q1/5K2/8/8/8/8/8 b - - 100 1', -30000),
    ]:
        assert search(chess.Board(fen), core)[0] == expected


def test_interruption_restores_real_position():
    board = chess.Board('3R4/5pbk/8/5p2/P7/2N3P1/1qn1NP1P/6K1 w - - 1 40')
    value, control = search(board, core, depth=6, nodes=512)
    assert value == 0 and control[1] and control[0] == 512
