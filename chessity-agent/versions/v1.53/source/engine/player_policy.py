"""Original learned move preference. It supplies bounded root-search bonuses only."""

import chess
import numpy as np

from engine.features import encode

SIZE = 935
VALUES = [0, 1, 3, 3.25, 5, 9, 0]


def encode_moves(board, moves):
    x = np.zeros((len(moves), SIZE), dtype=np.float32)
    x[:, :775] = encode(board)
    own, enemy = board.turn, not board.turn
    enemy_king = board.king(enemy)
    for i, move in enumerate(moves):
        source = move.from_square if own else chess.square_mirror(move.from_square)
        target = move.to_square if own else chess.square_mirror(move.to_square)
        x[i, 775 + source] = 1
        x[i, 839 + target] = 1
        piece = board.piece_type_at(move.from_square)
        captured = chess.PAWN if board.is_en_passant(move) else board.piece_type_at(move.to_square)
        x[i, 903 + piece - 1] = 1
        if captured:
            x[i, 909 + captured - 1] = 1
        if move.promotion:
            x[i, 915 + move.promotion - 2] = 1
        x[i, 919:935] = [
            board.gives_check(move),
            board.is_castling(move),
            board.is_en_passant(move),
            board.is_attacked_by(enemy, move.to_square),
            board.is_attacked_by(enemy, move.from_square),
            min(len(board.attackers(own, move.to_square)), 4) / 4,
            min(len(board.attackers(enemy, move.to_square)), 4) / 4,
            VALUES[captured or 0] / 9,
            VALUES[piece] / 9,
            (chess.square_rank(target) - chess.square_rank(source)) / 7,
            1 - chess.square_distance(move.to_square, enemy_king) / 7,
            1 - chess.square_distance(move.from_square, enemy_king) / 7,
            min(board.fullmove_number, 60) / 60,
            board.is_check(),
            abs(chess.square_file(target) - 3.5) / 3.5,
            min(board.halfmove_clock, 100) / 100,
        ]
    return x


class PlayerPolicy:
    def __init__(self, path):
        with np.load(path, allow_pickle=False) as data:
            self.p = [data[f"p{i}"].copy() for i in range(6)]
        w1, b1, w2, b2, w3, b3 = self.p
        if not (
            w1.ndim == 2
            and w1.shape[0] == SIZE
            and b1.shape == (w1.shape[1],)
            and w2.shape[0] == w1.shape[1]
            and b2.shape == (w2.shape[1],)
            and w3.shape == (w2.shape[1], 1)
            and b3.shape == (1,)
            and all(np.isfinite(p).all() for p in self.p)
        ):
            raise ValueError("Invalid player policy weights")

    def logits(self, board, moves):
        w1, b1, w2, b2, w3, b3 = self.p
        x = np.clip(encode_moves(board, moves) @ w1 + b1, 0, 1)
        x = np.clip(x @ w2 + b2, 0, 1)
        return (x @ w3 + b3)[:, 0]

    def bonuses(self, board, moves, max_cp=20):
        logits = self.logits(board, moves)
        # Relative log odds, capped to [0, max_cp]. No opponent or Elo labels.
        bonus = max_cp * np.clip(1 + (logits - logits.max()) / 4, 0, 1)
        return {move: int(round(value)) for move, value in zip(moves, bonus)}
