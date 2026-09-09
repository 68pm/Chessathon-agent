"""Original incremental piece bitsets for fast 0x88 attack queries."""

import numpy as np
from numba import njit, types
from numba.extending import intrinsic

BOARD_SIZE = 142
OCCUPANCY = 141
SQUARE_BITS = np.zeros(128, dtype=np.uint64)
PAWN_MASKS = np.zeros((2, 128), dtype=np.uint64)
KNIGHT_MASKS = np.zeros(128, dtype=np.uint64)
KING_MASKS = np.zeros(128, dtype=np.uint64)
RAYS = np.zeros((128, 8), dtype=np.uint64)
SLIDER_LINES = np.zeros((128, 2), dtype=np.uint64)
DIRECTIONS = np.array([-17, -16, -15, -1, 1, 15, 16, 17], dtype=np.int64)
for _square in range(128):
    if _square & 0x88:
        continue
    SQUARE_BITS[_square] = np.uint64(1) << np.uint64(_square // 16 * 8 + _square % 16)
for _square in range(128):
    if _square & 0x88:
        continue
    for _side_index, _side in enumerate((1, -1)):
        for _delta in (-1, 1):
            _source = _square - 16 * _side + _delta
            if _source >= 0 and not _source & 0x88:
                PAWN_MASKS[_side_index, _square] |= SQUARE_BITS[_source]
    for _delta in (-33, -31, -18, -14, 14, 18, 31, 33):
        _source = _square + _delta
        if _source >= 0 and not _source & 0x88:
            KNIGHT_MASKS[_square] |= SQUARE_BITS[_source]
    for _direction, _delta in enumerate(DIRECTIONS):
        _source = _square + int(_delta)
        if _source >= 0 and not _source & 0x88:
            KING_MASKS[_square] |= SQUARE_BITS[_source]
        while _source >= 0 and not _source & 0x88:
            RAYS[_square, _direction] |= SQUARE_BITS[_source]
            _source += int(_delta)
        _diagonal = int(_delta in (-17, -15, 15, 17))
        SLIDER_LINES[_square, _diagonal] |= RAYS[_square, _direction]


@intrinsic
def leading_zeros(typing_context, value):
    if value != types.uint64:
        return None
    def generate(context, builder, signature, args):
        # A typed false flag defines the zero-input result as64.
        zero_undefined = builder.icmp_unsigned('!=', args[0], args[0])
        return builder.ctlz(args[0], zero_undefined)
    return types.uint64(value), generate


@njit(cache=False)
def count_leading_zeros(value):
    return leading_zeros(value)


@njit(cache=False)
def rebuild_metadata(board):
    if len(board) != BOARD_SIZE:
        raise ValueError('Bitset board requires142slots')
    for index in range(128, BOARD_SIZE):
        board[index] = 0
    for square in range(128):
        if square & 0x88 or board[square] == 0:
            continue
        index = 134 + board[square]
        board[index] = np.int64(np.uint64(board[index]) | SQUARE_BITS[square])
        board[OCCUPANCY] = np.int64(np.uint64(board[OCCUPANCY]) | SQUARE_BITS[square])


@njit(cache=False, inline='always')
def set_square(board, square, piece):
    old = board[square]
    if old == piece:
        return
    bit = SQUARE_BITS[square]
    if old != 0:
        index = 134 + old
        board[index] = np.int64(np.uint64(board[index]) & ~bit)
    if piece != 0:
        index = 134 + piece
        board[index] = np.int64(np.uint64(board[index]) | bit)
    if (old == 0) != (piece == 0):
        board[OCCUPANCY] = np.int64(np.uint64(board[OCCUPANCY]) ^ bit)
    board[square] = piece


@njit(cache=False)
def attacked(board, square, side):
    if len(board) != BOARD_SIZE:
        raise ValueError('Bitset board requires142slots')
    if PAWN_MASKS[0 if side == 1 else 1, square] & np.uint64(board[134 + side]):
        return True
    if KNIGHT_MASKS[square] & np.uint64(board[134 + 2 * side]):
        return True
    if KING_MASKS[square] & np.uint64(board[134 + 6 * side]):
        return True
    queens = np.uint64(board[134 + 5 * side])
    bishops = np.uint64(board[134 + 3 * side]) | queens
    rooks = np.uint64(board[134 + 4 * side]) | queens
    if not ((bishops & SLIDER_LINES[square, 1]) | (rooks & SLIDER_LINES[square, 0])):
        return False
    occupancy = np.uint64(board[OCCUPANCY])
    for direction in range(8):
        delta = DIRECTIONS[direction]
        sliders = bishops if delta in (-17, -15, 15, 17) else rooks
        ray = RAYS[square, direction]
        if not (sliders & ray):
            continue
        blockers = occupancy & ray
        if blockers == 0:
            continue
        if delta > 0:
            nearest = blockers & (~blockers + np.uint64(1))
        else:
            nearest = np.uint64(1) << (np.uint64(63) - leading_zeros(blockers))
        if nearest & sliders:
            return True
    return False
