"""Try a legal king step before allocating a complete pseudo-legal move list."""
import ast


def transform(source):
    tree = ast.parse(source)
    function = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='has_legal_move')
    assert ast.unparse(function.body[1]) == 'side = state[0]'
    assert isinstance(function.body[2],ast.For)
    prefix = ast.parse('''
king = state[4 if side == 1 else 5]
for direction in KING:
    target = king + direction
    if target < 0 or target & 136:
        continue
    victim = board[target]
    if victim * side > 0 or abs(victim) == 6:
        continue
    move = encode_move(king, target)
    old = make(board, state, move)
    valid = not attacked(board, target, -side)
    unmake(board, state, move, old)
    if valid:
        return True
''').body
    function.body[2:2] = prefix
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)+'\n'
