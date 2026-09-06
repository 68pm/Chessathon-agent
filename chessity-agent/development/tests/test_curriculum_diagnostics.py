import chess

from scripts.curriculum_diagnostics import CASES, gold


def test_diagnostic_gold_is_verified_in_both_colours():
    for _, fen, kind in CASES:
        board = chess.Board(fen)
        for position in [board, board.mirror()]:
            before = position.fen()
            gold(position, kind)
            assert position.fen() == before
