import chess

VALUES = (0, 100, 320, 335, 500, 950, 20000)


def ordered(board, moves, tt_move, killers, history):
    def rank(move):
        if move == tt_move:
            return 10_000_000
        victim = board.piece_type_at(move.to_square)
        capture = victim is not None or board.is_en_passant(move)
        if capture or move.promotion:
            gain = VALUES[victim or (chess.PAWN if capture else 0)]
            attacker = VALUES[board.piece_type_at(move.from_square)]
            return 1_000_000 + 16 * gain - attacker + VALUES[move.promotion or 0]
        if move in killers:
            return 500_000 - killers.index(move)
        return history.get((board.turn, move.from_square, move.to_square), 0)
    return sorted(moves, key=rank, reverse=True)
