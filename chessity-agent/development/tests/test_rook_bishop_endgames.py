"""General conversion and rule-edge checks for the additional material class."""

import random
from pathlib import Path

import chess
import pytest

from experiments.elementary_endgames import ElementaryEndgames

DATA = Path(__file__).resolve().parents[1] / 'data/rook-bishop-syzygy-v1'
CASE = '5R2/7K/2r5/5k2/3b4/8/8/8 b - - 41 65'


@pytest.fixture
def endgames():
    if not (DATA / 'KRBvKR.rtbz').exists():
        pytest.skip('Acquire the verified rook-bishop dataset first.')
    helper = ElementaryEndgames(DATA, max_pieces=5)
    yield helper
    helper.close()


def resist(board, tables):
    """Independent opponent: preserve best WDL, delay zeroing if losing."""
    choices = []
    for move in list(board.legal_moves):
        board.push(move)
        outcome = board.outcome(claim_draw=True)
        if outcome:
            score, delay = (3 if outcome.winner is not None else 0), 0
        else:
            score = -tables.probe_wdl(board)
            delay = abs(tables.probe_dtz(board)) if score < 0 else 0
        board.pop()
        choices.append(((score, delay), move))
    return max(choices, key=lambda row: row[0])[1]


def convert(board, winning_color, endgames):
    initial = board.fen()
    for _ in range(400):
        if board.is_game_over(claim_draw=True):
            break
        before, stack = board.fen(), list(board.move_stack)
        if board.turn == winning_color:
            move = endgames.choose(board)
        else:
            move = resist(board, endgames.tables)
        assert board.fen() == before and board.move_stack == stack
        assert move in board.legal_moves, initial
        board.push(move)
    assert board.is_checkmate() and board.outcome().winner == winning_color, (initial, board.fen())


@pytest.mark.parametrize('mirrored', [False, True])
def test_measured_check_evasion_and_conversion(endgames, mirrored):
    board = chess.Board(CASE)
    if mirrored:
        board = board.mirror()
    expected = 'd5f3' if mirrored else 'd4f6'
    assert endgames.choose(board).uci() == expected
    convert(board, board.turn, endgames)


def test_random_won_material_class(endgames):
    rng, converted = random.Random(202609071043), 0
    for _ in range(30000):
        board = chess.Board(None)
        for square, piece in zip(rng.sample(range(64), 5), ['K', 'R', 'B', 'k', 'r']):
            board.set_piece_at(square, chess.Piece.from_symbol(piece))
        board.turn = bool(converted % 2)
        if not board.is_valid() or board.is_game_over():
            continue
        if endgames.tables.probe_wdl(board) != (2 if board.turn else -2):
            continue
        # Stay away from rounded-DTZ fifty-move ambiguity in this conversion drill.
        if abs(endgames.tables.probe_dtz(board)) > 70:
            continue
        if converted % 3 == 0:
            board = board.mirror()
            winner = chess.BLACK
        else:
            winner = chess.WHITE
        convert(board, winner, endgames)
        converted += 1
        if converted == 16:
            break
    assert converted == 16


def test_draw_and_fifty_move_fallback(endgames):
    drawn = chess.Board(CASE)
    drawn.push_uci('f5e4')
    assert endgames.tables.probe_wdl(drawn) == 0
    answer = endgames.choose(drawn)
    assert answer in drawn.legal_moves
    drawn.push(answer)
    assert endgames.tables.probe_wdl(drawn) == 0
    edge = chess.Board(CASE)
    edge.halfmove_clock = 80
    before = edge.fen()
    # No certified win within the remaining claim window: defer to normal search.
    assert endgames.choose(edge) is None
    assert edge.fen() == before
    edge.halfmove_clock = 98
    answer = endgames.choose(edge)
    assert answer in edge.legal_moves
    edge.push(answer)
    assert edge.outcome(claim_draw=True).winner is None


def test_missing_class_and_default_scope(endgames):
    board = chess.Board(CASE)
    default = ElementaryEndgames(DATA)
    missing = ElementaryEndgames(DATA.parent / 'elementary-syzygy', max_pieces=5)
    try:
        assert default.choose(board) is None
        assert missing.choose(board) is None
        assert board.fen() == CASE
        assert endgames.choose(chess.Board()) is None
    finally:
        default.close()
        missing.close()
