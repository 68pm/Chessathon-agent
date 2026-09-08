"""New interaction checks for an unchanged proven shortcut and check extensions."""
import json
import os
from pathlib import Path

import chess
import numpy as np
import pytest

os.environ['NUMBA_DISABLE_ERROR_MESSAGE_HIGHLIGHTING'] = '1'

from experiments import check_extensions_core as reference  # noqa: E402
from experiments import pawn_check_core as core  # noqa: E402
from experiments.aspiration_driver import arrays  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]


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
    assert not ac[1] and not bc[1] and a == b and np.array_equal(ac, bc)
