import chess
import numpy as np


def pressure_target(board):
    """Aggregate attack on king rings, no player identity or individual game imitation."""

    def pressure(color):
        king = board.king(not color)
        if king is None:
            return 0
        ring = chess.BB_KING_ATTACKS[king]
        return sum(
            (board.attacks_mask(sq) & ring).bit_count()
            for sq in chess.scan_forward(board.occupied_co[color])
        )

    return float(np.tanh((pressure(board.turn) - pressure(not board.turn)) / 8))
