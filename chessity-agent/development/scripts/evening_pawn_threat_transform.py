"""Protect threatening quiet pawn moves from late-move reduction."""
import ast

HELPER='''
@njit(cache=False, inline='always')
def pawn_threat_after_move(board, target, side, moved_piece):
    if moved_piece != side:
        return False
    if target // 16 == (6 if side == 1 else 1):
        return True
    for delta in (-1, 1):
        attacked_square = target + side * 16 + delta
        if attacked_square >= 0 and not attacked_square & 136 and board[attacked_square] * side < 0:
            return True
    return False
'''

def transform(source):
    marker='@njit(cache=False)\ndef search('
    assert source.count(marker)==1
    source=source.replace(marker,HELPER+'\n'+marker)
    old='''        if legal_count == 1 or quiescence:
'''
    new='''        if reduced and pawn_threat_after_move(board, target, side, old[0]):
            reduced = False
        if legal_count == 1 or quiescence:
'''
    assert source.count(old)==1
    source=source.replace(old,new)
    ast.parse(source)
    return source
