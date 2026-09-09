"""Integrate a frozen three-feature fit into the existing evaluation board scan."""
import math


def transform(source, physical):
    assert len(physical) == 3 and all(math.isfinite(v) for v in physical)
    assert all(0 <= v <= cap for v, cap in zip(physical, (25, 1, 1), strict=True))
    marker = '@njit(cache=False)\ndef classical(board, state, conversion=False):'
    helper = f'''CONTEXT_SHELTER = {float(physical[0])!r}
CONTEXT_MOBILITY_MG = {float(physical[1])!r}
CONTEXT_MOBILITY_EG = {float(physical[2])!r}

@njit(cache=False, inline='always')
def context_pawn_control(board, target, side):
    for delta in (-1, 1):
        source = target + 16 * side + delta
        if source >= 0 and (not source & 136) and board[source] == -side:
            return True
    return False

@njit(cache=False)
def context_shelter_gaps(pawns, king, side):
    gap = 0
    for file in range(max(0, king % 16 - 1), min(8, king % 16 + 2)):
        distance = 4
        rank = king // 16 + side
        while 0 <= rank < 8:
            if pawns & (np.uint64(1) << np.uint64(rank * 8 + file)):
                distance = abs(rank - king // 16)
                break
            rank += side
        gap += min(3, max(0, distance - 1))
    return gap

'''
    assert source.count(marker) == 1
    source = source.replace(marker, helper + marker)
    changes = {
        '    white_bishops, black_bishops = (0, 0)':
            '    white_bishops, black_bishops = (0, 0)\n    white_queens, black_queens = (0, 0)',
        '        if p == 3:\n            if c == 0:':
            '        if p == 5:\n            if c == 0:\n                white_queens += 1\n            else:\n                black_queens += 1\n        if p == 3:\n            if c == 0:',
        '            mobility, pressure, shield = (0, 0, 0)':
            '            mobility, pressure, shield = (0, 0, 0)\n            unsafe_mobility = 0',
        '                    mobility += int(victim * side <= 0)':
            '                    mobility += int(victim * side <= 0)\n                    if p != 6 and (CONTEXT_MOBILITY_MG != 0.0 or CONTEXT_MOBILITY_EG != 0.0):\n                        unsafe_mobility += int(victim * side <= 0 and context_pawn_control(board, target, side))',
        '                b += mobility * 2':
            '                b += mobility * 2\n                a -= CONTEXT_MOBILITY_MG * unsafe_mobility * (3 if p in (2, 3) else 1)\n                b -= CONTEXT_MOBILITY_EG * unsafe_mobility * 2',
        '    phase = min(24, phase)\n    value =':
            '    phase = min(24, phase)\n    if CONTEXT_SHELTER != 0.0:\n        shelter_white = context_shelter_gaps(white_pawns, state[4], 1) if black_queens else 0\n        shelter_black = context_shelter_gaps(black_pawns, state[5], -1) if white_queens else 0\n        mg -= CONTEXT_SHELTER * (shelter_white - shelter_black)\n    value =',
    }
    for before, after in changes.items():
        assert source.count(before) == 1, before
        source = source.replace(before, after)
    return source
