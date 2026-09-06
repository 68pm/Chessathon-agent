import chess

from engine.openings import ALIEN_LINE, alien_move
from engine.search import Search


def test_alien_repertoire_and_fallback():
    board = chess.Board()
    for san in ALIEN_LINE:
        expected = board.parse_san(san)
        before = board.fen()
        chosen = alien_move(board)
        assert chosen == (expected if board.turn == chess.WHITE else None)
        assert board.fen() == before
        board.push(expected)
    board.push_san("a6")
    assert alien_move(board) is None


def test_prepared_development_and_tactical_punishment():
    board = chess.Board()
    for san in ALIEN_LINE:
        board.push_san(san)
    for defense in ["e6", "Nbd7", "Ke8"]:
        trial = board.copy()
        trial.push_san(defense)
        assert alien_move(trial) == trial.parse_san("Bd3")
    board.push_san("Bg4")
    assert alien_move(board) == board.parse_san("Ne5+")
    board.push(alien_move(board))
    board.push_san("Ke8")
    assert alien_move(board) == board.parse_san("Nxg4")
    other = chess.Board()
    other.push_san("d4")
    other.push_san("Nf6")
    assert alien_move(other) is None


def test_transposition_and_castling_rights():
    board = chess.Board()
    for san in "e4 c6 d4 d5 Nc3 dxe4 Nxe4 Nf6 Ng5 h6".split():
        board.push_san(san)
    assert alien_move(board) == board.parse_san("Nxf7")
    board.castling_rights = 0
    assert alien_move(board) is None


def test_selective_opening_can_reject_the_knight_sacrifice():
    board = chess.Board()
    for san in ALIEN_LINE[:10]:
        board.push_san(san)
    before = board.fen()
    preferred = alien_move(board)
    assert preferred.uci() == "g5f7"
    result = Search().run(board, 5, max_depth=2, preferred_move=preferred, preference_cp=15)
    assert result.depth == 2 and result.move in board.legal_moves
    assert result.move != preferred
    assert board.fen() == before


def test_selective_hint_has_no_effect_in_emergency_fallback():
    board = chess.Board()
    baseline = Search().run(board, 0)
    hinted = Search().run(board, 0, preferred_move=board.parse_san("e4"), preference_cp=25)
    assert hinted.move == baseline.move
