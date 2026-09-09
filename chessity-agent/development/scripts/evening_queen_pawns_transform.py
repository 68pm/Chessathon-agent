"""Restore only the queen-imbalance passed-pawn correction on current fast core."""
import ast

def transform(source):
    tree=ast.parse(source)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='classical')
    lines=source.splitlines(keepends=True);part=''.join(lines[node.lineno-1:node.end_lineno])
    changes=[('    phase = 0\n','    white_queen, black_queen = False, False\n    phase = 0\n'),
        ('        phase += PHASE[p]\n','''        phase += PHASE[p]
        if p == 5:
            if c == 0:
                white_queen = True
            else:
                black_queen = True
'''),
        ('                b += r * r * 5\n','''                queen_imbalance = (black_queen and not white_queen) if side == 1 else (white_queen and not black_queen)
                multiplier = 2 if phase <= 8 and queen_imbalance else 5
                b += r * r * multiplier
''')]
    for old,new in changes:
        assert part.count(old)==1,old
        part=part.replace(old,new)
    lines[node.lineno-1:node.end_lineno]=[part]
    result=''.join(lines);ast.parse(result);return result
