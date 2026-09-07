"""Independent conversion checks against exact worst-resisting tablebase play."""

import random
from pathlib import Path

import chess
import pytest

from experiments.elementary_endgames import ElementaryEndgames

DATA = Path(__file__).resolve().parents[1] / 'data/elementary-syzygy'


@pytest.fixture
def endgames():
    if not (DATA / 'KQvK.rtbw').exists():
        pytest.skip('Download permitted elementary table data first.')
    helper = ElementaryEndgames(DATA)
    yield helper
    helper.close()


@pytest.mark.parametrize('piece', [chess.QUEEN, chess.ROOK])
def test_converts_random_wins_without_repetition(endgames, piece):
    rng = random.Random(2026090714 + piece)
    count = 0
    while count < 20:
        squares = rng.sample(range(64), 3)
        board = chess.Board(None)
        board.set_piece_at(squares[0], chess.Piece(chess.KING, chess.WHITE))
        board.set_piece_at(squares[1], chess.Piece(piece, chess.WHITE))
        board.set_piece_at(squares[2], chess.Piece(chess.KING, chess.BLACK))
        board.turn = bool(count % 2)
        if not board.is_valid() or board.is_game_over():
            continue
        if endgames.tables.probe_wdl(board) != (2 if board.turn else -2):
            continue
        initial = board.fen()
        for _ in range(150):
            outcome = board.outcome(claim_draw=True)
            if outcome:
                break
            before = board.fen()
            move = endgames.choose(board)
            assert board.fen() == before
            assert move in board.legal_moves
            board.push(move)
        assert board.is_checkmate() and board.outcome().winner == chess.WHITE, initial
        count += 1


def test_scope_and_promotion(endgames):
    assert endgames.choose(chess.Board()) is None
    board = chess.Board('8/4P3/4K3/8/8/8/8/k7 w - - 0 1')
    original = board.fen()
    move = endgames.choose(board)
    assert move in board.legal_moves and board.fen() == original
    board.push(move)
    assert endgames.tables.probe_wdl(board) == -2


def test_uses_actual_repetition_history(endgames):
    board = chess.Board('7k/8/8/8/8/8/8/KQ6 w - - 0 1')
    for uci in ['b1b2', 'h8g8', 'b2b1', 'g8h8', 'b1b2', 'h8g8', 'b2b1', 'g8h8']:
        board.push_uci(uci)
    assert board.is_repetition(3)
    # In a new near-repetition situation prefer a progressing win over a claimable draw.
    board.pop()
    board.pop()
    before = board.fen()
    move = endgames.choose(board)
    assert move in board.legal_moves and board.fen() == before
