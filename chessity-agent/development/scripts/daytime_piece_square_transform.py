"""Precompute the unchanged material and piece-square formula at module startup."""
import ast
import copy


def transform(source):
    tree=ast.parse(source)
    classical=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='classical')
    loop=next(n for n in classical.body if isinstance(n,ast.For)
        and any(isinstance(s,ast.Assign) and ast.unparse(s.targets[0])=='piece' for s in n.body))
    first=next(i for i,s in enumerate(loop.body) if isinstance(s,ast.Assign)
        and ast.unparse(s.targets[0])=='center')
    assert isinstance(loop.body[first+1],ast.If)
    assert ast.unparse(loop.body[first+2])=='a += MG[p]'
    assert ast.unparse(loop.body[first+3])=='b += EG[p]'
    formula=copy.deepcopy(loop.body[first:first+4])
    helper=ast.parse('''
def build_piece_square_tables():
    mg_table = np.zeros((13, 128), dtype=np.int64)
    eg_table = np.zeros((13, 128), dtype=np.int64)
    for piece in range(-6, 7):
        if piece == 0:
            continue
        for sq in range(128):
            if sq & 136:
                continue
            side = 1 if piece > 0 else -1
            p = abs(piece)
            f, rank = sq % 16, sq // 16
            r = rank if side == 1 else 7 - rank
            mg_table[piece + 6, sq] = a
            eg_table[piece + 6, sq] = b
    return mg_table, eg_table
''').body[0]
    inner=next(n for n in helper.body if isinstance(n,ast.For)).body[-1]
    inner.body[-2:-2]=formula
    loop.body[first:first+4]=ast.parse('''
a = PIECE_SQUARE_MG[piece + 6, sq]
b = PIECE_SQUARE_EG[piece + 6, sq]
''').body
    index=tree.body.index(classical)
    tree.body[index:index]=[helper,*ast.parse('PIECE_SQUARE_MG, PIECE_SQUARE_EG = build_piece_square_tables()').body]
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)+'\n'
