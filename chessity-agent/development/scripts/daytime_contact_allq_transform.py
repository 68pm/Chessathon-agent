"""Prove immediate quiet queen contact mates at every nonchecked quiescence node."""
import ast


def transform(source):
    tree=ast.parse(source)
    search=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='search')
    assert not any(isinstance(n,ast.FunctionDef) and n.name=='quiet_contact_mate' for n in tree.body)
    helper=ast.parse('''
@njit(cache=False)
def quiet_contact_mate(board, state):
    side = state[0]
    enemy = state[5 if side == 1 else 4]
    rank = enemy >> 4
    if (7 - rank if side == 1 else rank) < 2:
        return 0
    for source in range(128):
        if source & 136 or board[source] != 5 * side:
            continue
        for direction in KING:
            target = enemy + direction
            if target < 0 or target & 136 or board[target] != 0:
                continue
            dr = (target >> 4) - (source >> 4)
            df = (target & 7) - (source & 7)
            if dr == 0:
                step = 1 if df > 0 else -1
            elif df == 0:
                step = 16 if dr > 0 else -16
            elif abs(dr) == abs(df):
                step = (16 if dr > 0 else -16) + (1 if df > 0 else -1)
            else:
                continue
            square = source + step
            while square != target and board[square] == 0:
                square += step
            if square != target:
                continue
            move = encode_move(source, target)
            old = make(board, state, move)
            mate = (not attacked(board, state[4 if side == 1 else 5], -side)
                    and attacked(board, enemy, side) and not has_legal_move(board, state))
            unmake(board, state, move, old)
            if mate:
                return move
    return 0
''').body[0]
    tree.body.insert(tree.body.index(search),helper)
    block=next(n for n in search.body if isinstance(n,ast.If)
        and ast.unparse(n.test)=='quiescence and (not checked)')
    assert ast.unparse(block.body[0]).startswith('if not has_legal_move')
    block.body[1:1]=ast.parse('''
if quiet_contact_mate(board, state):
    return 30000 - ply - 1
''').body
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)+'\n'
