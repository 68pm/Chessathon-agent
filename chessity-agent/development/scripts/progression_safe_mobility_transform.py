"""Discount apparent mobility on squares controlled by enemy pawns."""


def transform(source):
    marker = '@njit(cache=False)\ndef classical(board, state, conversion=False):'
    helper = '''@njit(cache=False, inline='always')
def enemy_pawn_controls(board, target, side):
    for delta in (-1, 1):
        source = target + 16 * side + delta
        if source >= 0 and (not source & 136) and board[source] == -side:
            return True
    return False

'''
    assert source.count(marker) == 1
    source = source.replace(marker, helper + marker)
    old = '                    mobility += int(victim * side <= 0)'
    assert source.count(old) == 1
    return source.replace(old, '                    mobility += int(victim * side <= 0 and (not enemy_pawn_controls(board, target, side)))')
