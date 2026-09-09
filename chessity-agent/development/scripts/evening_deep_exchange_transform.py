"""Use the existing bounded SEE ordering at deep main-search nodes."""
import ast
from scripts.daytime_exchange_transform import HELPERS

def transform(source):
    marker='@njit(cache=False)\ndef order_moves('
    assert source.count(marker)==1;source=source.replace(marker,HELPERS+marker)
    old='def order_moves(board, moves, hint, killers, history, ply, side):'
    source=source.replace(old,old[:-2]+', state, exchange=False):')
    old='def order_moves_buffered(board, moves, hint, killers, history, ply, side, storage):'
    source=source.replace(old,old[:-2]+', state, exchange=False):')
    tree=ast.parse(source);lines=source.splitlines(keepends=True)
    for node in reversed([n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name in ('order_moves','order_moves_buffered')]):
        part=''.join(lines[node.lineno-1:node.end_lineno])
        marker='        elif move == killers[ply, 0]:'
        assert part.count(marker)==1
        part=part.replace(marker,'''            if exchange and captured and not promo and MG[abs(board[source])] > MG[captured]:
                estimate = bounded_exchange(board, state, move)
                if estimate < 0:
                    scores[i] = -100000 + estimate
'''+marker)
        lines[node.lineno-1:node.end_lineno]=[part]
    source=''.join(lines)
    old='order_moves_buffered(board, moves, hint, killers, history, ply, side, score_storage[ply])'
    assert source.count(old)==1
    source=source.replace(old,old[:-1]+', state, depth >= 3 and not checked)')
    old='order_moves(board, moves, previous, killers, history, 0, state[0])'
    assert source.count(old)==1
    source=source.replace(old,old[:-1]+', state, depth >= 3)')
    ast.parse(source);return source
