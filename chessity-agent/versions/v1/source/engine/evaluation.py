"""Original tapered evaluation. Scores are centipawns for the side to move."""
import chess

MG = (0, 100, 325, 340, 505, 975, 0)
EG = (0, 120, 310, 335, 530, 950, 0)
PHASE = (0, 0, 1, 1, 2, 4, 0)
PST = {}
for kind in range(1, 7):
    for square in range(64):
        f, r = chess.square_file(square), chess.square_rank(square)
        center = 7 - abs(2 * f - 7) - abs(2 * r - 7)
        if kind == chess.PAWN:
            mid, end = 6 * r + 2 * center, 10 * r + center
        elif kind == chess.KNIGHT:
            mid, end = 7 * center, 5 * center
        elif kind == chess.BISHOP:
            mid, end = 4 * center + 2 * r, 4 * center
        elif kind == chess.ROOK:
            mid, end = 2 * r + (15 if r == 6 else 0), 2 * center
        elif kind == chess.QUEEN:
            mid, end = center - max(0, r - 2) * 2, 3 * center
        else:
            mid = -5 * center - 8 * r + (22 if r == 0 and f in (1, 2, 6) else 0)
            end = 7 * center
        PST[kind, square] = (mid, end)


def phase(board):
    return min(24, sum(PHASE[k] * board.pieces_mask(k, c).bit_count()
                       for c in chess.COLORS for k in range(2, 6))) / 24


def classical(board):
    mg = eg = total_phase = 0
    for color in chess.COLORS:
        sign = 1 if color else -1
        own = board.occupied_co[color]
        pawns = board.pieces_mask(chess.PAWN, color)
        enemy_pawns = board.pieces_mask(chess.PAWN, not color)
        pawn_files = [(pawns & bb).bit_count() for bb in chess.BB_FILES]
        enemy_king = board.king(not color)
        ring = chess.BB_KING_ATTACKS[enemy_king] if enemy_king is not None else 0
        cmg = ceg = 0
        for kind in range(1, 7):
            pieces = board.pieces_mask(kind, color)
            count = pieces.bit_count()
            total_phase += PHASE[kind] * count
            cmg += MG[kind] * count
            ceg += EG[kind] * count
            if kind == chess.BISHOP and count >= 2:
                cmg += 28
                ceg += 40
            for sq in chess.scan_forward(pieces):
                rel = sq if color else chess.square_mirror(sq)
                a, b = PST[kind, rel]
                cmg += a
                ceg += b
                file, rank = chess.square_file(sq), chess.square_rank(rel)
                if kind == chess.PAWN:
                    if pawn_files[file] > 1:
                        cmg -= 10
                        ceg -= 16
                    adjacent = ((chess.BB_FILES[file - 1] if file else 0) |
                                (chess.BB_FILES[file + 1] if file < 7 else 0))
                    if not pawns & adjacent:
                        cmg -= 12
                        ceg -= 10
                    ahead = (chess.BB_ALL << (8 * (chess.square_rank(sq) + 1))) & chess.BB_ALL if color else (1 << (8 * chess.square_rank(sq))) - 1
                    if not enemy_pawns & ahead & (adjacent | chess.BB_FILES[file]):
                        cmg += rank * rank * 2
                        ceg += rank * rank * 5
                    continue
                attacks = board.attacks_mask(sq)
                if kind != chess.KING:
                    mobility = (attacks & ~own).bit_count()
                    cmg += mobility * (3 if kind in (2, 3) else 1)
                    ceg += mobility * 2
                    cmg += (attacks & ring).bit_count() * (7 if kind in (2, 3) else 5)
                if kind == chess.ROOK and pawn_files[file] == 0:
                    bonus = 12 if enemy_pawns & chess.BB_FILES[file] else 22
                    cmg += bonus
                    ceg += bonus // 2
                if kind == chess.KING:
                    shield = chess.BB_KING_ATTACKS[sq] & pawns
                    cmg += 9 * shield.bit_count()
        mg += sign * cmg
        eg += sign * ceg
    p = min(24, total_phase)
    value = (mg * p + eg * (24 - p)) / 24
    return round(value if board.turn else -value)


def style_score(board, move):
    """Root-only heuristic; never added to primary search values."""
    color = board.turn
    forcing = 12 * board.gives_check(move) + 2 * board.is_capture(move)
    board.push(move)
    try:
        king = board.king(board.turn)
        ring = chess.BB_KING_ATTACKS[king] if king is not None else 0
        pressure = sum((board.attacks_mask(s) & ring).bit_count()
                       for s in chess.scan_forward(board.occupied_co[color]))
        return forcing + 3 * pressure
    finally:
        board.pop()


class Evaluator:
    def __init__(self, mode='classical', model=None):
        self.mode = mode
        self.model = model

    def __call__(self, board):
        base = classical(board)
        if self.mode == 'classical' or self.model is None:
            return base
        neural = self.model.centipawns(board)
        if self.mode == 'neural':
            return neural
        mix = 0.20 if self.mode == 'hybrid' else 0.10 + 0.20 * phase(board)
        return round(base * (1 - mix) + neural * mix)
