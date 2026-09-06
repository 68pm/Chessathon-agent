"""775 features, canonicalised to the mover's colour. Mirror parity is exact."""

import chess
import numpy as np

from engine.evaluation import phase

SIZE = 775


def encode(board):
    x = np.zeros(SIZE, dtype=np.float32)
    # Own pieces are channels 0..5; opposing pieces 6..11; ranks face forward.
    for sq, piece in board.piece_map().items():
        channel = piece.piece_type - 1 + (0 if piece.color == board.turn else 6)
        rel = sq if board.turn else chess.square_mirror(sq)
        x[channel * 64 + rel] = 1
    # Relative side-to-move is always 'own'; constant makes the convention explicit.
    x[768] = 1
    x[769:773] = [
        board.has_kingside_castling_rights(board.turn),
        board.has_queenside_castling_rights(board.turn),
        board.has_kingside_castling_rights(not board.turn),
        board.has_queenside_castling_rights(not board.turn),
    ]
    x[773] = board.has_legal_en_passant()
    x[774] = phase(board)
    return x
