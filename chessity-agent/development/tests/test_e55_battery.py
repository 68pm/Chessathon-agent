"""Independent bitboard-ray oracle and propagation checks for the threat trigger."""
import ast
import io
import json
from pathlib import Path

import chess
import chess.pgn
import numpy as np

from experiments import e55_battery_core as core
from experiments.aspiration_driver import arrays

ROOT = Path(__file__).resolve().parents[1]


def oracle(board):
    for colour in [True, False]:
        king = board.king(not colour)
        ring = chess.BB_KING_ATTACKS[king] | chess.BB_SQUARES[king]
        for queen in board.pieces(chess.QUEEN, colour):
            for bishop in board.pieces(chess.BISHOP, colour):
                if abs(chess.square_file(queen) - chess.square_file(bishop)) != abs(chess.square_rank(queen) - chess.square_rank(bishop)):
                    continue
                if chess.between(queen, bishop) & board.occupied:
                    continue
                direction = (chess.square_file(bishop) > chess.square_file(queen),
                             chess.square_rank(bishop) > chess.square_rank(queen))
                for square in chess.SquareSet(ring & chess.ray(queen, bishop)):
                    if (chess.square_file(square) > chess.square_file(queen),
                        chess.square_rank(square) > chess.square_rank(queen)) != direction:
                        continue
                    if chess.square_distance(queen, square) < chess.square_distance(queen, bishop):
                        continue
                    if not (chess.between(bishop, square) & board.occupied):
                        return True
    return False


def check(board):
    pieces, state = arrays(board)
    before = pieces.copy(), state.copy()
    assert bool(core.bishop_queen_battery.py_func(pieces, state)) == oracle(board)
    assert np.array_equal(pieces, before[0]) and np.array_equal(state, before[1])


def test_all_four_actual_games_and_mirrors():
    path = ROOT / ('runs/improvement-loop-20260907/competition-conditional-rated-01/'
                   'rated-compiled-near-queen-checks-v1/results.json')
    count = 0
    for row in json.loads(path.read_text())['games']:
        game = chess.pgn.read_game(io.StringIO(row['pgn']))
        board = game.board()
        for move in game.mainline_moves():
            board.push(move)
            check(board)
            check(board.mirror())
            count += 1
    assert count >= 470


def test_loss_battery_and_intervening_blockers():
    board = chess.Board('3rr1k1/pp4pp/1nq1p3/8/2PPB3/B2Q4/5PPP/R5K1 b - - 0 22')
    assert oracle(board)
    check(board)
    for piece in [chess.Piece(chess.PAWN, True), chess.Piece(chess.PAWN, False)]:
        blocked = board.copy()
        blocked.set_piece_at(chess.F5, piece)
        assert not oracle(blocked)
        check(blocked)
    board.remove_piece_at(chess.E4)
    assert not oracle(board)
    check(board)


def test_initial_position_and_bare_kings_have_no_trigger():
    for board in [chess.Board(), chess.Board('4k3/8/8/8/8/8/8/4K3 w - - 0 1')]:
        assert not oracle(board)
        check(board)


def test_only_search_and_new_helper_changed_credit_reaches_all_recursions():
    old = ast.parse((ROOT / 'candidates/compiled-near-queen-checks-v1/engine/compiled_core.py').read_text())
    new = ast.parse(Path(core.__file__).read_text())
    def unchanged(tree):
        return [ast.dump(n) for n in tree.body if not (isinstance(n, ast.FunctionDef)
                and n.name in ['search', 'bishop_queen_battery'])]
    assert unchanged(old) == unchanged(new)
    search = next(n for n in new.body if isinstance(n, ast.FunctionDef) and n.name == 'search')
    calls = [n for n in ast.walk(search) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'search']
    assert len(calls) == 4 and all(len(n.args) == 28 and n.args[-1].id == 'threats_left' for n in calls)
