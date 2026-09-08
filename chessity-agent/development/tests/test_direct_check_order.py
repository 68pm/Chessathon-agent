"""Independent check geometry and completed-search parity for ordering only."""
import json
import os
import random
from pathlib import Path

import chess
import numpy as np
import pytest

os.environ['NUMBA_DISABLE_ERROR_MESSAGE_HIGHLIGHTING'] = '1'

from experiments import check_extensions_core as reference  # noqa: E402
from experiments import direct_check_order_core as core  # noqa: E402
from experiments.aspiration_driver import arrays, decode  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


def encoding(move):
    a, b = move.from_square, move.to_square
    return a // 8 * 16 + a % 8 | (b // 8 * 16 + b % 8) << 7


def test_direct_geometry_matches_moved_piece_attacks_without_mutation():
    rng, board, checked = random.Random(2026090825), chess.Board(), 0
    for _ in range(240):
        if board.is_game_over(claim_draw=True) or board.fullmove_number > 70:
            board.reset()
        pieces, state = arrays(board)
        saved = pieces.copy()
        king = board.king(not board.turn)
        for move in list(board.legal_moves):
            if board.is_capture(move) or move.promotion or board.is_castling(move):
                continue
            board.push(move)
            expected = king in board.attacks(move.to_square)
            board.pop()
            actual = core.direct_quiet_check(pieces, encoding(move), state[0], state[5 if state[0] == 1 else 4])
            assert bool(actual) == expected, (board.fen(), move.uci())
            checked += 1
        assert np.array_equal(pieces, saved)
        board.push(rng.choice(list(board.legal_moves)))
    assert checked >= 1000


def test_ordering_preserves_hint_capture_and_killer_priorities_and_state():
    rows = [json.loads(line) for line in (ROOT / 'runs/improvement-loop-20260907/cycle-20/roots.jsonl').read_text().splitlines()]
    count = 0
    for row in rows:
        board = chess.Board(row['fen'])
        pieces, state = arrays(board)
        moves = core.generate(pieces, state, False)
        before_p, before_s, before_m = pieces.copy(), state.copy(), moves.copy()
        quiet = [int(m) for m in moves if not board.is_capture(decode(int(m))) and not decode(int(m)).promotion]
        killers = np.zeros((100, 2), dtype=np.int64)
        if len(quiet) >= 2:
            killers[0] = quiet[:2]
        history = np.full((2, 128, 128), 500000, dtype=np.int64)
        hint = int(moves[-1])
        a = reference.order_moves(pieces, moves, hint, killers, history, 0, state[0])
        b = core.order_moves(pieces, moves, hint, killers, history, 0, state[0], state[5 if state[0] == 1 else 4])
        for index, encoded in enumerate(moves):
            move = decode(int(encoded))
            if int(encoded) == hint or board.is_capture(move) or move.promotion or int(encoded) in killers[0]:
                assert a[index] == b[index]
            elif b[index] != a[index]:
                assert 500000 < b[index] < 800000
                count += 1
        assert np.array_equal(pieces, before_p) and np.array_equal(state, before_s)
        assert np.array_equal(moves, before_m)
    assert count > 0


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


@pytest.mark.parametrize('index', [0, 5, 8, 13, 14, 16])
def test_completed_full_window_score_matches_parent(index):
    row = [json.loads(line) for line in (ROOT / 'runs/improvement-loop-20260907/cycle-20/roots.jsonl').read_text().splitlines()][index]
    board = chess.Board(row['start_fen'])
    for uci in row['history']:
        board.push_uci(uci)
    assert board.fen() == row['fen'] and board.is_valid()
    a, ac = search(board, reference)
    b, bc = search(board, core)
    assert not ac[1] and not bc[1] and a == b


def test_draw_and_mate_precedence():
    for fen, expected in [('7k/5Q2/6K1/8/8/8/8/8 b - - 0 1', 0),
                          ('7k/6Q1/5K2/8/8/8/8/8 b - - 100 1', -30000)]:
        board = chess.Board(fen)
        assert board.is_valid()
        assert search(board, core)[0] == expected


def test_interrupted_search_restores_real_position():
    board = chess.Board('3R4/5pbk/8/5p2/P7/2N3P1/1qn1NP1P/6K1 w - - 1 40')
    value, control = search(board, core, depth=6, nodes=512)
    assert value == 0 and control[1] and control[0] == 512
