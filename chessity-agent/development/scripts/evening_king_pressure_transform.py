"""Transfer only the original bounded coordinated attack term into fastv1.56."""
import ast

def transform(source):
    tree=ast.parse(source)
    node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='classical')
    lines=source.splitlines(keepends=True)
    part=''.join(lines[node.lineno-1:node.end_lineno])
    replacements=[
        ('    phase = 0\n','    white_queen, black_queen = False, False\n    white_units, black_units = 0, 0\n    white_attackers, black_attackers = 0, 0\n    phase = 0\n'),
        ('        phase += PHASE[p]\n','        phase += PHASE[p]\n        if p == 5:\n            if c == 0:\n                white_queen = True\n            else:\n                black_queen = True\n'),
        ('            if p != 6:\n','''            if p != 6:
                if pressure > 0:
                    units = pressure * (2 if p in (2, 3) else 3 if p == 4 else 5)
                    if side == 1:
                        white_units += units
                        white_attackers += 1
                    else:
                        black_units += units
                        black_attackers += 1
'''),
        ('    value = (mg * phase + eg * (24 - phase)) / 24.0\n','''    value = (mg * phase + eg * (24 - phase)) / 24.0
    if white_queen and white_attackers >= 2:
        value += min(250, 2 * white_units * white_units)
    if black_queen and black_attackers >= 2:
        value -= min(250, 2 * black_units * black_units)
''')]
    for old,new in replacements:
        assert part.count(old)==1,old
        part=part.replace(old,new)
    lines[node.lineno-1:node.end_lineno]=[part]
    changed=''.join(lines)
    ast.parse(changed)
    return changed
