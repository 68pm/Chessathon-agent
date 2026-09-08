"""Independent pawn-support oracle, mirrors, restoration and exact scope."""
import ast
import importlib.util
import io
import json
from pathlib import Path

import chess
import chess.pgn
import numpy as np

from experiments import e55_connected_passers_core as core
from experiments.aspiration_driver import arrays

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'candidates/compiled-near-queen-checks-v1/engine/compiled_core.py'
spec = importlib.util.spec_from_file_location('e55_passer_parent', BASE)
parent = importlib.util.module_from_spec(spec)
spec.loader.exec_module(parent)


def oracle(board):
    if board.queens:
        return 0
    value = 0
    for side in [True, False]:
        for sq in board.pieces(chess.PAWN, side):
            ahead = [p for p in board.pieces(chess.PAWN, not side)
                     if abs(chess.square_file(p) - chess.square_file(sq)) <= 1
                     and ((chess.square_rank(p) > chess.square_rank(sq)) if side else
                          (chess.square_rank(p) < chess.square_rank(sq)))]
            if not ahead and board.attackers(side, sq) & board.pieces(chess.PAWN, side):
                rank = chess.square_rank(sq) if side else 7 - chess.square_rank(sq)
                value += (1 if side else -1) * 2 * rank * rank
    phase = sum(len(board.pieces(p, c)) * w for c in [True, False]
                for p, w in [(chess.KNIGHT, 1), (chess.BISHOP, 1), (chess.ROOK, 2)])
    return value * (24 - min(24, phase)) / 24 * (1 if board.turn else -1)


def check(board):
    pieces, state = arrays(board)
    before = pieces.copy(), state.copy()
    delta = core.classical.py_func(pieces, state) - parent.classical.py_func(pieces, state)
    assert abs(delta - oracle(board)) <= 1
    assert np.array_equal(pieces, before[0]) and np.array_equal(state, before[1])
    assert core.classical.py_func(*arrays(board)) == core.classical.py_func(*arrays(board.mirror()))


def test_all_actual_games():
    source = ROOT / 'runs/improvement-loop-20260907/competition-conditional-rated-01/rated-compiled-near-queen-checks-v1/results.json'
    count = 0
    for row in json.loads(source.read_text())['games']:
        game = chess.pgn.read_game(io.StringIO(row['pgn']))
        board = game.board()
        for move in game.mainline_moves():
            board.push(move)
            check(board)
            count += 1
    assert count >= 470


def test_draw_c5_creates_supported_passers_while_bc1_does_not():
    board = chess.Board('4r1k1/3b1pp1/1P5p/8/2PP3P/BB3RP1/4r3/6K1 w - - 5 35')
    previous = oracle(board)
    board.push_san('Bc1')
    assert -oracle(board) == previous
    board.pop()
    board.push_san('c5')
    assert -oracle(board) > previous
    check(board)


def test_queen_presence_and_unpassed_pawns_exclude_bonus():
    for fen in ['4k3/8/2p5/1P6/2P5/8/8/4K3 w - - 0 1',
                '4k3/8/8/1P6/2P5/8/8/3QK3 w - - 0 1']:
        board = chess.Board(fen)
        assert oracle(board) == 0
        check(board)


def test_only_classical_function_changes():
    def other(text):
        return [ast.dump(n) for n in ast.parse(text).body if not (isinstance(n, ast.FunctionDef) and n.name == 'classical')]
    assert other(BASE.read_text()) == other(Path(core.__file__).read_text())
