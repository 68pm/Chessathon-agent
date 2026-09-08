"""Independent square-set oracle for queenless king activity; no recursive JIT."""
import ast
import importlib.util
import json
from pathlib import Path

import chess
import numpy as np

from experiments import competition_king_targets_core as core
from experiments.aspiration_driver import arrays

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'candidates/compiled-near-queen-checks-v1/engine/compiled_core.py'
spec = importlib.util.spec_from_file_location('king_targets_parent', BASE)
parent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parent)


def oracle(board):
    phase = sum(len(board.pieces(kind, side)) * weight for side in [True, False]
        for kind, weight in [(chess.KNIGHT, 1), (chess.BISHOP, 1), (chess.ROOK, 2), (chess.QUEEN, 4)])
    if board.queens or phase > 8:
        return 0
    distances = []
    for side in [True, False]:
        targets = [sq for sq in board.pieces(chess.PAWN, not side)
            if not (board.attackers(not side, sq) & board.pieces(chess.PAWN, not side))]
        distances.append(min((chess.square_distance(board.king(side), sq) for sq in targets), default=7))
    return 16 * (distances[1] - distances[0]) * (24 - phase) / 24 * (1 if board.turn else -1)


def check(board):
    pieces, state = arrays(board)
    before = pieces.copy(), state.copy()
    for conversion in [False, True]:
        value = core.classical.py_func(pieces, state, conversion)
        previous = parent.classical.py_func(pieces, state, conversion)
        # Parent rounds after tapering; an integer difference can differ by1.
        assert abs((value - previous) - oracle(board)) <= 1
    assert np.array_equal(pieces, before[0]) and np.array_equal(state, before[1])
    assert core.classical.py_func(*arrays(board), False) == core.classical.py_func(*arrays(board.mirror()), False)


def test_all_recent_game_positions_and_mirrors():
    import chess.pgn

    count = 0
    for path in sorted((ROOT / 'runs/competition-review-20260908/source').glob('*.pgn')):
        with path.open(encoding='utf-8') as stream:
            game = chess.pgn.read_game(stream)
        board = game.board()
        for move in game.mainline_moves():
            board.push(move)
            check(board)
            count += 1
    assert count > 800


def test_activity_towards_weak_pawn_is_rewarded_in_draw_root():
    rows = [json.loads(s) for s in (ROOT / 'runs/competition-review-20260908/targets.jsonl').read_text().splitlines()]
    board = chess.Board(rows[-1]['fen'])
    current = oracle(board)
    board.push_san('Kg4')
    assert -oracle(board) > current
    check(board)


def test_queens_and_bare_kings_add_nothing():
    for fen in ['4k3/8/8/8/8/8/4P3/3QK3 w - - 0 1', '4k3/8/8/8/8/8/8/4K3 w - - 0 1']:
        board = chess.Board(fen)
        assert oracle(board) == 0
        check(board)


def test_every_other_function_and_constant_is_identical_to_selected53():
    def other(text):
        return [ast.dump(n) for n in ast.parse(text).body
            if not (isinstance(n, ast.FunctionDef) and n.name == 'classical')]
    assert other(BASE.read_text()) == other(Path(core.__file__).read_text())
