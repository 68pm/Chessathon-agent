"""Original 0x88 chess core. Numba compiles this readable Python in memory.

This is our implementation, not a translation of an external chess engine.
Piece codes are signed pawn=1 through king=6; squares are rank*16+file.
No disk JIT cache, external engine, pretrained network or background worker.
"""
import time
import numpy as np
from numba import njit, objmode
KNIGHT = np.array([-33, -31, -18, -14, 14, 18, 31, 33], dtype=np.int64)
KING = np.array([-17, -16, -15, -1, 1, 15, 16, 17], dtype=np.int64)
BISHOP = np.array([-17, -15, 15, 17], dtype=np.int64)
ROOK = np.array([-16, -1, 1, 16], dtype=np.int64)
MG = np.array([0, 100, 325, 340, 505, 975, 0], dtype=np.int64)
EG = np.array([0, 120, 310, 335, 530, 950, 0], dtype=np.int64)
PHASE = np.array([0, 0, 1, 1, 2, 4, 0], dtype=np.int64)
_rng = np.random.default_rng(2026090714)
ZPIECE = _rng.integers(1, 2 ** 63, (13, 128), dtype=np.uint64)
ZCASTLE = _rng.integers(1, 2 ** 63, 16, dtype=np.uint64)
ZEP = _rng.integers(1, 2 ** 63, 128, dtype=np.uint64)
ZSIDE = np.uint64(16253881494669371445)

@njit(cache=False)
def attacked(board, square, side):
    for d in (-17, -15):
        s = square + d * side
        if s >= 0 and (not s & 136) and (board[s] == side):
            return True
    for d in KNIGHT:
        s = square + d
        if s >= 0 and (not s & 136) and (board[s] == 2 * side):
            return True
    for d in KING:
        s = square + d
        if s >= 0 and (not s & 136) and (board[s] == 6 * side):
            return True
    for d in KING:
        s = square + d
        diagonal = d in (-17, -15, 15, 17)
        while s >= 0 and (not s & 136):
            p = board[s]
            if p:
                if p == 5 * side or p == (3 if diagonal else 4) * side:
                    return True
                break
            s += d
    return False

@njit(cache=False)
def encode_move(source, target, promo=0, flags=0):
    return source | target << 7 | promo << 14 | flags << 17

@njit(cache=False)
def generate(board, state, captures=False):
    moves = np.empty(256, dtype=np.int64)
    n = 0
    side, rights, ep = (state[0], state[1], state[2])
    for source in range(128):
        if source & 136 or board[source] * side <= 0:
            continue
        piece = abs(board[source])
        if piece == 1:
            step = 16 * side
            target = source + step
            promotion = target // 16 in (0, 7)
            if not target & 136 and board[target] == 0:
                if promotion:
                    for p in (5, 4, 3, 2):
                        moves[n] = encode_move(source, target, p)
                        n += 1
                elif not captures:
                    moves[n] = encode_move(source, target)
                    n += 1
                    if source // 16 == (1 if side == 1 else 6) and board[target + step] == 0:
                        moves[n] = encode_move(source, target + step, 0, 4)
                        n += 1
            for d in (step - 1, step + 1):
                target = source + d
                if target < 0 or target & 136:
                    continue
                if board[target] * side < 0 and abs(board[target]) != 6:
                    if target // 16 in (0, 7):
                        for p in (5, 4, 3, 2):
                            moves[n] = encode_move(source, target, p)
                            n += 1
                    else:
                        moves[n] = encode_move(source, target)
                        n += 1
                elif target == ep and board[target] == 0 and (board[target - step] == -side):
                    moves[n] = encode_move(source, target, 0, 1)
                    n += 1
        else:
            directions = KNIGHT if piece == 2 else BISHOP if piece == 3 else ROOK if piece == 4 else KING
            for d in directions:
                target = source + d
                while target >= 0 and (not target & 136):
                    victim = board[target]
                    if victim * side > 0 or abs(victim) == 6:
                        break
                    if not captures or victim:
                        moves[n] = encode_move(source, target)
                        n += 1
                    if victim or piece in (2, 6):
                        break
                    target += d
            if piece == 6 and (not captures):
                home = 4 if side == 1 else 116
                if source == home and (not attacked(board, home, -side)):
                    offset = 0 if side == 1 else 112
                    if rights & (1 if side == 1 else 4) and board[offset + 7] == 4 * side and (board[offset + 5] == 0) and (board[offset + 6] == 0) and (not attacked(board, offset + 5, -side)) and (not attacked(board, offset + 6, -side)):
                        moves[n] = encode_move(source, offset + 6, 0, 2)
                        n += 1
                    if rights & (2 if side == 1 else 8) and board[offset] == 4 * side and (board[offset + 1] == 0) and (board[offset + 2] == 0) and (board[offset + 3] == 0) and (not attacked(board, offset + 3, -side)) and (not attacked(board, offset + 2, -side)):
                        moves[n] = encode_move(source, offset + 2, 0, 2)
                        n += 1
    return moves[:n]

@njit(cache=False)
def make(board, state, move):
    source, target = (move & 127, move >> 7 & 127)
    promo, flags = (move >> 14 & 7, move >> 17)
    piece, captured = (board[source], board[target])
    old = (piece, captured, state[1], state[2], state[3], state[4], state[5])
    side = state[0]
    board[target] = side * promo if promo else piece
    board[source] = 0
    if flags & 1:
        board[target - 16 * side] = 0
    if flags & 2:
        rfrom = source // 16 * 16 + (7 if target > source else 0)
        rto = source + (1 if target > source else -1)
        board[rto], board[rfrom] = (board[rfrom], 0)
    rights = state[1]
    if abs(piece) == 6:
        state[4 if side == 1 else 5] = target
        rights &= 12 if side == 1 else 3
    for square, bit in ((0, 2), (7, 1), (112, 8), (119, 4)):
        if source == square or target == square:
            rights &= 15 ^ bit
    state[1] = rights
    state[2] = source + 16 * side if flags & 4 else -1
    state[3] = 0 if abs(piece) == 1 or captured or flags & 1 else state[3] + 1
    state[0] = -side
    return old

@njit(cache=False)
def unmake(board, state, move, old):
    source, target = (move & 127, move >> 7 & 127)
    flags = move >> 17
    side = -state[0]
    board[source], board[target] = (old[0], old[1])
    if flags & 1:
        board[target - 16 * side] = -side
    if flags & 2:
        rfrom = source // 16 * 16 + (7 if target > source else 0)
        rto = source + (1 if target > source else -1)
        board[rfrom], board[rto] = (board[rto], 0)
    state[0] = side
    for i in range(1, 6):
        state[i] = old[i + 1]

@njit(cache=False)
def legal_moves(board, state):
    moves = generate(board, state)
    n = 0
    side = state[0]
    for move in moves.copy():
        old = make(board, state, move)
        valid = not attacked(board, state[4 if side == 1 else 5], -side)
        unmake(board, state, move, old)
        if valid:
            moves[n] = move
            n += 1
    return moves[:n]

@njit(cache=False)
def has_legal_move(board, state):
    """Terminal checks need one legal reply, not a fully validated move list."""
    side = state[0]
    for move in generate(board, state):
        old = make(board, state, move)
        valid = not attacked(board, state[4 if side == 1 else 5], -side)
        unmake(board, state, move, old)
        if valid:
            return True
    return False

@njit(cache=False)
def perft(board, state, depth):
    if depth == 0:
        return 1
    total = 0
    for move in legal_moves(board, state):
        old = make(board, state, move)
        total += perft(board, state, depth - 1)
        unmake(board, state, move, old)
    return total

@njit(cache=False)
def position_hash(board, state):
    key = ZCASTLE[state[1]]
    if state[0] == -1:
        key ^= ZSIDE
    for square in range(128):
        if not square & 136 and board[square]:
            key ^= ZPIECE[board[square] + 6, square]
    ep, side = (state[2], state[0])
    if ep >= 0:
        for delta in (-1, 1):
            source = ep - 16 * side + delta
            victim = ep - 16 * side
            if source >= 0 and (not source & 136) and (board[source] == side) and (board[victim] == -side):
                board[source], board[victim], board[ep] = (0, 0, side)
                valid = not attacked(board, state[4 if side == 1 else 5], -side)
                board[source], board[victim], board[ep] = (side, -side, 0)
                if valid:
                    key ^= ZEP[ep]
                    break
    return key

@njit(cache=False)
def insufficient(board):
    knights, bishops, colour = (0, 0, -1)
    for square in range(128):
        if square & 136:
            continue
        p = abs(board[square])
        if p in (1, 4, 5):
            return False
        if p == 2:
            knights += 1
        if p == 3:
            bishops += 1
            c = square // 16 + square % 16 & 1
            if colour == -1:
                colour = c
            elif colour != c:
                colour = 2
    return bishops == 0 and knights <= 1 or (knights == 0 and colour != 2)
PAWN_FILES = np.zeros(8, dtype=np.uint64)
PASSED_PAWN_MASKS = np.zeros((2, 128), dtype=np.uint64)
for _file in range(8):
    PAWN_FILES[_file] = np.uint64(72340172838076673 << _file)
for _colour in range(2):
    for _square in range(128):
        if _square & 136:
            continue
        _rank, _file = (_square // 16, _square % 16)
        _mask = 0
        for _ahead in range(_rank + 1, 8) if _colour == 0 else range(_rank):
            for _adjacent in range(max(0, _file - 1), min(8, _file + 2)):
                _mask |= 1 << 8 * _ahead + _adjacent
        PASSED_PAWN_MASKS[_colour, _square] = np.uint64(_mask)

@njit(cache=False, inline='always')
def pawn_file_count(pawns, file):
    mask = pawns & PAWN_FILES[file]
    if mask == 0:
        return 0
    return 1 + int(mask & mask - np.uint64(1) != 0)

GEOMETRY_WEIGHTS = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0], dtype=np.float64)

@njit(cache=False)
def geometry_popcount(bits):
    count = 0
    while bits:
        bits &= bits - np.uint64(1)
        count += 1
    return count

@njit(cache=False)
def geometry_side(cover, double, units, attackers, enemy_occupied, enemy_pawns, king, enemy_side, phase, push, fork):
    zone = np.uint64(0)
    shield = 0
    for d in KING:
        target = king + d
        if target >= 0 and not target & 136:
            bit = np.uint64(1) << np.uint64(target // 16 * 8 + target % 16)
            zone |= bit
            if (target // 16 - king // 16) * enemy_side == 1 and enemy_pawns & bit:
                shield += 1
    escapes = geometry_popcount(zone & ~enemy_occupied & ~cover)
    rank = king // 16 if enemy_side == 1 else 7 - king // 16
    return (units / 16., units * max(0, attackers - 1) / 64.,
            geometry_popcount(cover) / 8., geometry_popcount(double) / 8.,
            units * max(0, 3 - escapes) / 48., units * (24 - phase) / 384.,
            units * max(0, 3 - shield) / 48., rank * units / 112.,
            push / 975., fork / 975.)

@njit(cache=False)
def classical_geometry(board, state, conversion=False):
    """Equivalent to the preserved v1.14 tapered evaluator; optional conversion term."""
    white_pawns = np.uint64(0)
    black_pawns = np.uint64(0)
    white_bishops, black_bishops = (0, 0)
    white_material, black_material = (0, 0)
    phase = 0
    occupied_w, occupied_b = np.uint64(0), np.uint64(0)
    cover_w, cover_b = np.uint64(0), np.uint64(0)
    double_w, double_b = np.uint64(0), np.uint64(0)
    units_w, units_b, attackers_w, attackers_b = 0, 0, 0, 0
    pushes_w, pushes_b, forks_w, forks_b = 0, 0, 0, 0
    queens = 0
    for sq in range(128):
        if sq & 136 or board[sq] == 0:
            continue
        p = abs(board[sq])
        c = 0 if board[sq] > 0 else 1
        phase += PHASE[p]
        bit = np.uint64(1) << np.uint64(sq // 16 * 8 + sq % 16)
        if c == 0:
            occupied_w |= bit
        else:
            occupied_b |= bit
        queens += int(p == 5)
        if c == 0:
            white_material += MG[p]
        else:
            black_material += MG[p]
        if p == 1:
            if c == 0:
                white_pawns |= np.uint64(1) << np.uint64(sq // 16 * 8 + sq % 16)
            else:
                black_pawns |= np.uint64(1) << np.uint64(sq // 16 * 8 + sq % 16)
        if p == 3:
            if c == 0:
                white_bishops += 1
            else:
                black_bishops += 1
    mg = 28 * (int(white_bishops >= 2) - int(black_bishops >= 2))
    eg = 40 * (int(white_bishops >= 2) - int(black_bishops >= 2))
    for sq in range(128):
        piece = board[sq]
        if sq & 136 or piece == 0:
            continue
        side = 1 if piece > 0 else -1
        c, enemy = (0, 1) if side == 1 else (1, 0)
        p = abs(piece)
        f, rank = (sq % 16, sq // 16)
        r = rank if side == 1 else 7 - rank
        center = 7 - abs(2 * f - 7) - abs(2 * r - 7)
        if p == 1:
            a, b = (6 * r + 2 * center, 10 * r + center)
        elif p == 2:
            a, b = (7 * center, 5 * center)
        elif p == 3:
            a, b = (4 * center + 2 * r, 4 * center)
        elif p == 4:
            a, b = (2 * r + (15 if r == 6 else 0), 2 * center)
        elif p == 5:
            a, b = (center - max(0, r - 2) * 2, 3 * center)
        else:
            a = -5 * center - 8 * r + (22 if r == 0 and f in (1, 2, 6) else 0)
            b = 7 * center
        a += MG[p]
        b += EG[p]
        if p == 1:
            if queens:
                enemy_king = state[5 if side == 1 else 4]
                touched = False
                for delta in (-1, 1):
                    target = sq + 16 * side + delta
                    if target >= 0 and not target & 136 and max(abs(target % 16 - enemy_king % 16), abs(target // 16 - enemy_king // 16)) == 1:
                        bit = np.uint64(1) << np.uint64(target // 16 * 8 + target % 16)
                        touched = True
                        if side == 1:
                            double_w |= cover_w & bit
                            cover_w |= bit
                        else:
                            double_b |= cover_b & bit
                            cover_b |= bit
                if touched:
                    if side == 1:
                        units_w += 1
                        attackers_w += 1
                    else:
                        units_b += 1
                        attackers_b += 1
                push = sq + 16 * side
                if push >= 0 and not push & 136 and board[push] == 0 and 0 < push // 16 < 7:
                    victims, value = 0, 0
                    for delta in (-1, 1):
                        target = push + 16 * side + delta
                        if target >= 0 and not target & 136 and board[target] * side < -1 and abs(board[target]) < 6:
                            victims += 1
                            value += MG[abs(board[target])]
                    if victims:
                        board[sq], board[push] = 0, side
                        safe = not attacked(board, state[4 if side == 1 else 5], -side) and (not attacked(board, push, -side) or attacked(board, push, side))
                        board[sq], board[push] = side, 0
                        if safe:
                            if side == 1:
                                pushes_w += value
                                forks_w += value if victims >= 2 else 0
                            else:
                                pushes_b += value
                                forks_b += value if victims >= 2 else 0
            if pawn_file_count(white_pawns if c == 0 else black_pawns, f) > 1:
                a -= 10
                b -= 16
            if (f == 0 or pawn_file_count(white_pawns if c == 0 else black_pawns, f - 1) == 0) and (f == 7 or pawn_file_count(white_pawns if c == 0 else black_pawns, f + 1) == 0):
                a -= 12
                b -= 10
            passed = (black_pawns if c == 0 else white_pawns) & PASSED_PAWN_MASKS[c, sq] == 0
            if passed:
                a += r * r * 2
                b += r * r * 5
        else:
            ek = state[5 if side == 1 else 4]
            directions = KNIGHT if p == 2 else BISHOP if p == 3 else ROOK if p == 4 else KING
            mobility, pressure, shield = (0, 0, 0)
            for d in directions:
                target = sq + d
                while target >= 0 and (not target & 136):
                    victim = board[target]
                    mobility += int(victim * side <= 0)
                    near_king = max(abs(target % 16 - ek % 16), abs(target // 16 - ek // 16)) == 1
                    pressure += int(near_king)
                    if queens and near_king:
                        bit = np.uint64(1) << np.uint64(target // 16 * 8 + target % 16)
                        if side == 1:
                            double_w |= cover_w & bit
                            cover_w |= bit
                        else:
                            double_b |= cover_b & bit
                            cover_b |= bit
                    shield += int(victim == side)
                    if victim or p in (2, 6):
                        break
                    target += d
            if queens and pressure and p != 6:
                units = 2 if p in (2, 3) else 3 if p == 4 else 5
                if side == 1:
                    units_w += units
                    attackers_w += 1
                else:
                    units_b += units
                    attackers_b += 1
            if p != 6:
                a += mobility * (3 if p in (2, 3) else 1) + pressure * (7 if p in (2, 3) else 5)
                b += mobility * 2
            else:
                a += 9 * shield
            if p == 4 and pawn_file_count(white_pawns if c == 0 else black_pawns, f) == 0:
                bonus = 12 if pawn_file_count(white_pawns if enemy == 0 else black_pawns, f) else 22
                a += bonus
                b += bonus // 2
        mg += side * a
        eg += side * b
    phase = min(24, phase)
    value = (mg * phase + eg * (24 - phase)) / 24.0
    if conversion and (white_material == 0 or black_material == 0) and (max(white_material, black_material) >= 500):
        strong = 0 if white_material > black_material else 1
        own, enemy = (state[4 + strong], state[5 - strong])
        edge = min(enemy % 16, 7 - enemy % 16, enemy // 16, 7 - enemy // 16)
        distance = max(abs(own % 16 - enemy % 16), abs(own // 16 - enemy // 16))
        value += (1 if strong == 0 else -1) * (40 * (3 - edge) + 12 * (7 - distance))
    base = int(round(value * state[0]))
    if not queens:
        return base, (0., 0., 0., 0., 0., 0., 0., 0., 0., 0.)
    w = geometry_side(cover_w, double_w, units_w, attackers_w, occupied_b, black_pawns, state[5], -1, phase, pushes_w, forks_w)
    b = geometry_side(cover_b, double_b, units_b, attackers_b, occupied_w, white_pawns, state[4], 1, phase, pushes_b, forks_b)
    return base, ((w[0] - b[0]) * state[0], (w[1] - b[1]) * state[0], (w[2] - b[2]) * state[0], (w[3] - b[3]) * state[0], (w[4] - b[4]) * state[0], (w[5] - b[5]) * state[0], (w[6] - b[6]) * state[0], (w[7] - b[7]) * state[0], (w[8] - b[8]) * state[0], (w[9] - b[9]) * state[0])

@njit(cache=False)
def classical(board, state, conversion=False):
    """Equivalent to the preserved v1.14 tapered evaluator; optional conversion term."""
    white_pawns = np.uint64(0)
    black_pawns = np.uint64(0)
    white_bishops, black_bishops = (0, 0)
    white_material, black_material = (0, 0)
    phase = 0
    for sq in range(128):
        if sq & 136 or board[sq] == 0:
            continue
        p = abs(board[sq])
        c = 0 if board[sq] > 0 else 1
        phase += PHASE[p]
        if c == 0:
            white_material += MG[p]
        else:
            black_material += MG[p]
        if p == 1:
            if c == 0:
                white_pawns |= np.uint64(1) << np.uint64(sq // 16 * 8 + sq % 16)
            else:
                black_pawns |= np.uint64(1) << np.uint64(sq // 16 * 8 + sq % 16)
        if p == 3:
            if c == 0:
                white_bishops += 1
            else:
                black_bishops += 1
    mg = 28 * (int(white_bishops >= 2) - int(black_bishops >= 2))
    eg = 40 * (int(white_bishops >= 2) - int(black_bishops >= 2))
    for sq in range(128):
        piece = board[sq]
        if sq & 136 or piece == 0:
            continue
        side = 1 if piece > 0 else -1
        c, enemy = (0, 1) if side == 1 else (1, 0)
        p = abs(piece)
        f, rank = (sq % 16, sq // 16)
        r = rank if side == 1 else 7 - rank
        center = 7 - abs(2 * f - 7) - abs(2 * r - 7)
        if p == 1:
            a, b = (6 * r + 2 * center, 10 * r + center)
        elif p == 2:
            a, b = (7 * center, 5 * center)
        elif p == 3:
            a, b = (4 * center + 2 * r, 4 * center)
        elif p == 4:
            a, b = (2 * r + (15 if r == 6 else 0), 2 * center)
        elif p == 5:
            a, b = (center - max(0, r - 2) * 2, 3 * center)
        else:
            a = -5 * center - 8 * r + (22 if r == 0 and f in (1, 2, 6) else 0)
            b = 7 * center
        a += MG[p]
        b += EG[p]
        if p == 1:
            if pawn_file_count(white_pawns if c == 0 else black_pawns, f) > 1:
                a -= 10
                b -= 16
            if (f == 0 or pawn_file_count(white_pawns if c == 0 else black_pawns, f - 1) == 0) and (f == 7 or pawn_file_count(white_pawns if c == 0 else black_pawns, f + 1) == 0):
                a -= 12
                b -= 10
            passed = (black_pawns if c == 0 else white_pawns) & PASSED_PAWN_MASKS[c, sq] == 0
            if passed:
                a += r * r * 2
                b += r * r * 5
        else:
            ek = state[5 if side == 1 else 4]
            directions = KNIGHT if p == 2 else BISHOP if p == 3 else ROOK if p == 4 else KING
            mobility, pressure, shield = (0, 0, 0)
            for d in directions:
                target = sq + d
                while target >= 0 and (not target & 136):
                    victim = board[target]
                    mobility += int(victim * side <= 0)
                    pressure += int(max(abs(target % 16 - ek % 16), abs(target // 16 - ek // 16)) == 1)
                    shield += int(victim == side)
                    if victim or p in (2, 6):
                        break
                    target += d
            if p != 6:
                a += mobility * (3 if p in (2, 3) else 1) + pressure * (7 if p in (2, 3) else 5)
                b += mobility * 2
            else:
                a += 9 * shield
            if p == 4 and pawn_file_count(white_pawns if c == 0 else black_pawns, f) == 0:
                bonus = 12 if pawn_file_count(white_pawns if enemy == 0 else black_pawns, f) else 22
                a += bonus
                b += bonus // 2
        mg += side * a
        eg += side * b
    phase = min(24, phase)
    value = (mg * phase + eg * (24 - phase)) / 24.0
    if conversion and (white_material == 0 or black_material == 0) and (max(white_material, black_material) >= 500):
        strong = 0 if white_material > black_material else 1
        own, enemy = (state[4 + strong], state[5 - strong])
        edge = min(enemy % 16, 7 - enemy % 16, enemy // 16, 7 - enemy // 16)
        distance = max(abs(own % 16 - enemy % 16), abs(own // 16 - enemy // 16))
        value += (1 if strong == 0 else -1) * (40 * (3 - edge) + 12 * (7 - distance))
    return int(round(value * state[0]))

@njit(cache=False)
def evaluate(board, state, weights, bias, output, blend, conversion):
    if blend == 0.:
        return classical(board, state, conversion)
    accumulator = build_accumulator(board, state, weights, bias)
    return evaluate_accumulator(board, state, output, blend, conversion, accumulator)

@njit(cache=False)
def add_feature(accumulator, weights, piece, square, multiplier, state):
    if piece == 0:
        return
    for perspective in range(2):
        side = 1 if perspective == 0 else -1
        p = piece * side
        king = state[4 + perspective]
        king_rank = king // 16 if side == 1 else 7 - king // 16
        flip_file = king % 16 >= 4
        king_file = 7 - king % 16 if flip_file else king % 16
        bucket = king_rank // 2 * 2 + king_file // 2
        file = 7 - square % 16 if flip_file else square % 16
        rel = (square // 16 if side == 1 else 7 - square // 16) * 8 + file
        feature = 1 + bucket * 768 + (abs(p) - 1 + (6 if p < 0 else 0)) * 64 + rel
        for j in range(weights.shape[1]):
            accumulator[perspective, j] += multiplier * weights[feature, j]

@njit(cache=False)
def build_accumulator(board, state, weights, bias):
    has_queen = False
    for square in range(128):
        if not square & 136 and abs(board[square]) == 5:
            has_queen = True
            break
    if not has_queen:
        return np.zeros((2, len(bias)), dtype=np.float64)
    accumulator = np.empty((2, len(bias)), dtype=np.float64)
    for c in range(2):
        for j in range(len(bias)):
            accumulator[c, j] = bias[j]
    for square in range(128):
        if not square & 136 and board[square]:
            add_feature(accumulator, weights, board[square], square, 1, state)
    return accumulator


@njit(cache=False)
def king_context(square, side):
    rank = square // 16 if side == 1 else 7 - square // 16
    flip = square % 16 >= 4
    file = 7 - square % 16 if flip else square % 16
    return (rank // 2 * 2 + file // 2) * 2 + int(flip)


@njit(cache=False)
def add_perspective(accumulator, weights, piece, square, multiplier, state, perspective):
    if piece == 0:
        return
    side = 1 if perspective == 0 else -1
    p = piece * side
    king = state[4 + perspective]
    rank = king // 16 if side == 1 else 7 - king // 16
    flip = king % 16 >= 4
    file = 7 - king % 16 if flip else king % 16
    bucket = rank // 2 * 2 + file // 2
    rel = (square // 16 if side == 1 else 7 - square // 16) * 8 + (7 - square % 16 if flip else square % 16)
    feature = 1 + bucket * 768 + (abs(p) - 1 + (6 if p < 0 else 0)) * 64 + rel
    for j in range(weights.shape[1]):
        accumulator[perspective, j] += multiplier * weights[feature, j]


@njit(cache=False)
def refresh_perspective(accumulator, weights, bias, board, state, perspective):
    for j in range(len(bias)):
        accumulator[perspective, j] = bias[j]
    for square in range(128):
        if not square & 136 and board[square]:
            add_perspective(accumulator, weights, board[square], square, 1, state, perspective)


@njit(cache=False)
def update_accumulator(accumulator, weights, move, old, direction, board, state, bias):
    source, target = (move & 127, move >> 7 & 127)
    promo, flags = (move >> 14 & 7, move >> 17)
    piece, captured = (old[0], old[1])
    old_queens = accumulator[0, 32]
    queens = old_queens + direction * (int(promo == 5) - int(abs(captured) == 5))
    if queens == 0:
        if old_queens != 0:
            accumulator.fill(0.)
        return
    if old_queens == 0:
        rebuilt = build_accumulator(board, state, weights, bias)
        for c in range(2):
            for j in range(len(bias)):
                accumulator[c, j] = rebuilt[c, j]
        return
    side = 1 if piece > 0 else -1
    if abs(piece) == 6 and king_context(source, side) != king_context(target, side):
        moved = 0 if side == 1 else 1
        refresh_perspective(accumulator, weights, bias, board, state, moved)
        other = 1 - moved
        add_perspective(accumulator, weights, piece, source, -direction, state, other)
        add_perspective(accumulator, weights, captured, target, -direction, state, other)
        add_perspective(accumulator, weights, piece, target, direction, state, other)
        if flags & 2:
            rfrom = source // 16 * 16 + (7 if target > source else 0)
            rto = source + (1 if target > source else -1)
            add_perspective(accumulator, weights, 4 * side, rfrom, -direction, state, other)
            add_perspective(accumulator, weights, 4 * side, rto, direction, state, other)
        return
    add_feature(accumulator, weights, piece, source, -direction, state)
    add_feature(accumulator, weights, captured, target, -direction, state)
    add_feature(accumulator, weights, side * promo if promo else piece, target, direction, state)
    if flags & 1:
        add_feature(accumulator, weights, -side, target - 16 * side, -direction, state)
    if flags & 2:
        rfrom = source // 16 * 16 + (7 if target > source else 0)
        rto = source + (1 if target > source else -1)
        add_feature(accumulator, weights, 4 * side, rfrom, -direction, state)
        add_feature(accumulator, weights, 4 * side, rto, direction, state)

@njit(cache=False)
def shared_residual(board, state, base, features, output, accumulator):
    phase, pawns, queens, blocked = 0, 0, 0, 0
    for square in range(128):
        if square & 136 or not board[square]:
            continue
        piece = board[square]
        kind = abs(piece)
        phase += PHASE[kind]
        queens += int(kind == 5)
        if kind == 1:
            pawns += 1
            target = square + (16 if piece > 0 else -16)
            if 2 <= square % 16 <= 5 and target >= 0 and not target & 136 and board[target] == -piece:
                blocked += 1
    if not queens:
        return 0.
    context = (min(24, phase) / 24., blocked / 8., pawns / 16., queens / 2.)
    c = 0 if state[0] == 1 else 1
    first, second = np.empty(32, dtype=np.float64), np.empty(32, dtype=np.float64)
    for j in range(32):
        common = output[j]
        for k in range(4):
            common += context[k] * output[384 + k * 32 + j]
        geometric = max(-1., min(1., base / 1000.)) * output[32 + 10 * 32 + j]
        for k in range(10):
            geometric += features[k] * output[32 + k * 32 + j]
        first[j] = max(0., accumulator[c, j] + common + geometric)
        second[j] = max(0., accumulator[1 - c, j] + common - geometric)
    raw = 0.
    for j in range(16):
        a, b = output[1024 + j], output[1024 + j]
        for k in range(32):
            weight = output[512 + k * 16 + j]
            a += first[k] * weight
            b += second[k] * weight
        raw += .5 * (max(0., a) - max(0., b)) * output[1040 + j]
    return 300. * np.tanh(raw)


@njit(cache=False)
def evaluate_accumulator(board, state, output, blend, conversion, accumulator):
    if blend == 0. or accumulator[0, 32] == 0:
        return classical(board, state, conversion)
    base, features = classical_geometry(board, state, conversion)
    return base + int(round(blend * shared_residual(board, state, base, features, output, accumulator)))

@njit(cache=False)
def clock_now():
    with objmode(value='float64'):
        value = time.perf_counter()
    return value

@njit(cache=False)
def order_moves(board, moves, hint, killers, history, ply, side):
    scores = np.empty(len(moves), dtype=np.int64)
    for i, move in enumerate(moves):
        source, target = (move & 127, move >> 7 & 127)
        captured = abs(board[target]) if not move >> 17 & 1 else 1
        promo = move >> 14 & 7
        if move == hint:
            scores[i] = 10000000
        elif captured or promo:
            scores[i] = 1000000 + 16 * (MG[captured] + MG[promo]) - MG[abs(board[source])]
        elif move == killers[ply, 0]:
            scores[i] = 900000
        elif move == killers[ply, 1]:
            scores[i] = 800000
        else:
            scores[i] = history[0 if side == 1 else 1, source, target]
    return scores

@njit(cache=False)
def generate_buffered(board, state, captures, storage):
    moves = storage
    n = 0
    side, rights, ep = (state[0], state[1], state[2])
    for source in range(128):
        if source & 136 or board[source] * side <= 0:
            continue
        piece = abs(board[source])
        if piece == 1:
            step = 16 * side
            target = source + step
            promotion = target // 16 in (0, 7)
            if not target & 136 and board[target] == 0:
                if promotion:
                    for p in (5, 4, 3, 2):
                        assert n < len(moves), 'Move storage exhausted'
                        moves[n] = encode_move(source, target, p)
                        n += 1
                elif not captures:
                    assert n < len(moves), 'Move storage exhausted'
                    moves[n] = encode_move(source, target)
                    n += 1
                    if source // 16 == (1 if side == 1 else 6) and board[target + step] == 0:
                        assert n < len(moves), 'Move storage exhausted'
                        moves[n] = encode_move(source, target + step, 0, 4)
                        n += 1
            for d in (step - 1, step + 1):
                target = source + d
                if target < 0 or target & 136:
                    continue
                if board[target] * side < 0 and abs(board[target]) != 6:
                    if target // 16 in (0, 7):
                        for p in (5, 4, 3, 2):
                            assert n < len(moves), 'Move storage exhausted'
                            moves[n] = encode_move(source, target, p)
                            n += 1
                    else:
                        assert n < len(moves), 'Move storage exhausted'
                        moves[n] = encode_move(source, target)
                        n += 1
                elif target == ep and board[target] == 0 and (board[target - step] == -side):
                    assert n < len(moves), 'Move storage exhausted'
                    moves[n] = encode_move(source, target, 0, 1)
                    n += 1
        else:
            directions = KNIGHT if piece == 2 else BISHOP if piece == 3 else ROOK if piece == 4 else KING
            for d in directions:
                target = source + d
                while target >= 0 and (not target & 136):
                    victim = board[target]
                    if victim * side > 0 or abs(victim) == 6:
                        break
                    if not captures or victim:
                        assert n < len(moves), 'Move storage exhausted'
                        moves[n] = encode_move(source, target)
                        n += 1
                    if victim or piece in (2, 6):
                        break
                    target += d
            if piece == 6 and (not captures):
                home = 4 if side == 1 else 116
                if source == home and (not attacked(board, home, -side)):
                    offset = 0 if side == 1 else 112
                    if rights & (1 if side == 1 else 4) and board[offset + 7] == 4 * side and (board[offset + 5] == 0) and (board[offset + 6] == 0) and (not attacked(board, offset + 5, -side)) and (not attacked(board, offset + 6, -side)):
                        assert n < len(moves), 'Move storage exhausted'
                        moves[n] = encode_move(source, offset + 6, 0, 2)
                        n += 1
                    if rights & (2 if side == 1 else 8) and board[offset] == 4 * side and (board[offset + 1] == 0) and (board[offset + 2] == 0) and (board[offset + 3] == 0) and (not attacked(board, offset + 3, -side)) and (not attacked(board, offset + 2, -side)):
                        assert n < len(moves), 'Move storage exhausted'
                        moves[n] = encode_move(source, offset + 2, 0, 2)
                        n += 1
    return moves[:n]

@njit(cache=False)
def order_moves_buffered(board, moves, hint, killers, history, ply, side, storage):
    assert len(storage) >= len(moves), 'Score storage exhausted'
    scores = storage[:len(moves)]
    for i, move in enumerate(moves):
        source, target = (move & 127, move >> 7 & 127)
        captured = abs(board[target]) if not move >> 17 & 1 else 1
        promo = move >> 14 & 7
        if move == hint:
            scores[i] = 10000000
        elif captured or promo:
            scores[i] = 1000000 + 16 * (MG[captured] + MG[promo]) - MG[abs(board[source])]
        elif move == killers[ply, 0]:
            scores[i] = 900000
        elif move == killers[ply, 1]:
            scores[i] = 800000
        else:
            scores[i] = history[0 if side == 1 else 1, source, target]
    return scores


@njit(cache=False)
def cached_evaluation(board, state, output, blend, conversion, accumulator, key,
                      value_keys, value_scores, value_valid):
    slot = int(key & np.uint64(len(value_keys) - 1))
    if value_valid[slot] and value_keys[slot] == key:
        return value_scores[slot]
    value = evaluate_accumulator(board, state, output, blend, conversion, accumulator)
    value_keys[slot] = key
    value_scores[slot] = value
    value_valid[slot] = True
    return value


@njit(cache=False)
def search(board, state, depth, alpha, beta, ply, qdepth, hashes, hlen, context, ttkey, ttcontext, ttdata, killers, history, control, deadline, weights, bias, output, blend, conversion, reductions, accumulator, move_storage, score_storage, value_keys, value_scores, value_valid):
    control[0] += 1
    if control[0] >= control[2] or (control[0] & 1023 == 0 and clock_now() >= deadline):
        control[1] = 1
    if control[1]:
        return 0
    side = state[0]
    checked = attacked(board, state[4 if side == 1 else 5], -side)
    key = hashes[hlen - 1]
    repetitions = 0
    for i in range(max(0, hlen - state[3] - 1), hlen):
        repetitions += int(hashes[i] == key)
    if state[3] >= 100 or repetitions >= 3 or insufficient(board):
        if checked and (not has_legal_move(board, state)):
            return -30000 + ply
        return 0
    if ply >= 96:
        return (-30000 + ply if checked else 0) if not has_legal_move(board, state) else cached_evaluation(board, state, output, blend, conversion, accumulator, key, value_keys, value_scores, value_valid)
    quiescence = depth <= 0
    slot = int(key & np.uint64(len(ttkey) - 1))
    hint = 0
    original_alpha = alpha
    if not quiescence and ttkey[slot] == key and (ttcontext[slot] == context) and (ttdata[slot, 4] == state[3]):
        hint = ttdata[slot, 3]
        if ttdata[slot, 0] >= depth:
            value = ttdata[slot, 1]
            value = value - ply if value > 29000 else value + ply if value < -29000 else value
            bound = ttdata[slot, 2]
            if bound == 0 or (bound == 1 and value >= beta) or (bound == 2 and value <= alpha):
                return value
    stand = -31000
    if quiescence and (not checked):
        if not has_legal_move(board, state):
            return 0
        stand = cached_evaluation(board, state, output, blend, conversion, accumulator, key, value_keys, value_scores, value_valid)
        if qdepth >= 12 or stand >= beta:
            return stand
        alpha = max(alpha, stand)
    moves = generate_buffered(board, state, quiescence and (not checked), move_storage[ply])
    scores = order_moves_buffered(board, moves, hint, killers, history, ply, side, score_storage[ply])
    best, bestmove, legal_count = (stand, 0, 0)
    for index in range(len(moves)):
        choice = index
        for k in range(index + 1, len(moves)):
            if scores[k] > scores[choice]:
                choice = k
        moves[index], moves[choice] = (moves[choice], moves[index])
        scores[index], scores[choice] = (scores[choice], scores[index])
        move = moves[index]
        target = move >> 7 & 127
        quiet = board[target] == 0 and (not move >> 14 & 7) and (not move >> 17 & 1)
        old = make(board, state, move)
        if attacked(board, state[4 if side == 1 else 5], -side):
            unmake(board, state, move, old)
            continue
        legal_count += 1
        if blend != 0.0:
            update_accumulator(accumulator, weights, move, old, 1, board, state, bias)
        childkey = position_hash(board, state)
        hashes[hlen] = childkey
        childcontext = childkey if state[3] == 0 or state[1] != old[2] else context + childkey
        nextdepth = depth - 1
        reduced = reductions and (not quiescence) and (depth >= 3) and (legal_count >= 5) and quiet and (not checked) and (not attacked(board, state[4 if state[0] == 1 else 5], side))
        if legal_count == 1 or quiescence:
            value = -search(board, state, nextdepth, -beta, -alpha, ply + 1, qdepth + 1 if quiescence else 0, hashes, hlen + 1, childcontext, ttkey, ttcontext, ttdata, killers, history, control, deadline, weights, bias, output, blend, conversion, reductions, accumulator, move_storage, score_storage, value_keys, value_scores, value_valid)
        else:
            value = -search(board, state, nextdepth - int(reduced), -alpha - 1, -alpha, ply + 1, 0, hashes, hlen + 1, childcontext, ttkey, ttcontext, ttdata, killers, history, control, deadline, weights, bias, output, blend, conversion, reductions, accumulator, move_storage, score_storage, value_keys, value_scores, value_valid)
            if reduced and value > alpha and (not control[1]):
                value = -search(board, state, nextdepth, -alpha - 1, -alpha, ply + 1, 0, hashes, hlen + 1, childcontext, ttkey, ttcontext, ttdata, killers, history, control, deadline, weights, bias, output, blend, conversion, reductions, accumulator, move_storage, score_storage, value_keys, value_scores, value_valid)
            if value > alpha and value < beta and (not control[1]):
                value = -search(board, state, nextdepth, -beta, -alpha, ply + 1, 0, hashes, hlen + 1, childcontext, ttkey, ttcontext, ttdata, killers, history, control, deadline, weights, bias, output, blend, conversion, reductions, accumulator, move_storage, score_storage, value_keys, value_scores, value_valid)
        unmake(board, state, move, old)
        if blend != 0.0:
            update_accumulator(accumulator, weights, move, old, -1, board, state, bias)
        if control[1]:
            return 0
        if value > best:
            best, bestmove = (value, move)
        alpha = max(alpha, value)
        if alpha >= beta:
            if quiet and (not quiescence):
                if killers[ply, 0] != move:
                    killers[ply, 1], killers[ply, 0] = (killers[ply, 0], move)
                source = move & 127
                hside = 0 if side == 1 else 1
                history[hside, source, target] = min(500000, history[hside, source, target] + depth * depth)
            break
    if legal_count == 0 and (not quiescence or checked):
        return -30000 + ply if checked else 0
    if not quiescence:
        packed = best + ply if best > 29000 else best - ply if best < -29000 else best
        ttkey[slot], ttcontext[slot] = (key, context)
        ttdata[slot, 0], ttdata[slot, 1] = (depth, packed)
        ttdata[slot, 2] = 2 if best <= original_alpha else 1 if best >= beta else 0
        ttdata[slot, 3], ttdata[slot, 4] = (bestmove, state[3])
    return best

@njit(cache=False)
def root_iteration(board, state, depth, previous, moves, bonuses, hashes, hlen, ttkey, ttcontext, ttdata, killers, history, control, deadline, weights, bias, output, blend, conversion, reductions, move_storage, score_storage, value_keys, value_scores, value_valid):
    accumulator = build_accumulator(board, state, weights, bias)
    context = np.uint64(0)
    for i in range(max(0, hlen - state[3] - 1), hlen):
        context += hashes[i]
    order = order_moves(board, moves, previous, killers, history, 0, state[0])
    best, bestmove = (-31000, previous)
    for index in range(len(moves)):
        choice = index
        for k in range(index + 1, len(moves)):
            if order[k] > order[choice]:
                choice = k
        move, bonus = (moves[choice], bonuses[choice])
        moves[choice], moves[index] = (moves[index], moves[choice])
        bonuses[choice], bonuses[index] = (bonuses[index], bonuses[choice])
        order[choice], order[index] = (order[index], order[choice])
        old = make(board, state, move)
        if blend != 0.0:
            update_accumulator(accumulator, weights, move, old, 1, board, state, bias)
        key = position_hash(board, state)
        hashes[hlen] = key
        ctx = key if state[3] == 0 or state[1] != old[2] else context + key
        cutoff = best if abs(best) >= 29000 else best - bonus
        value = -search(board, state, depth - 1, -31000, -cutoff, 1, 0, hashes, hlen + 1, ctx, ttkey, ttcontext, ttdata, killers, history, control, deadline, weights, bias, output, blend, conversion, reductions, accumulator, move_storage, score_storage, value_keys, value_scores, value_valid)
        unmake(board, state, move, old)
        if blend != 0.0:
            update_accumulator(accumulator, weights, move, old, -1, board, state, bias)
        if control[1]:
            return (previous, 0, False)
        if abs(value) < 29000:
            value += bonus
        if value > best:
            best, bestmove = (value, move)
    return (bestmove, best, True)
