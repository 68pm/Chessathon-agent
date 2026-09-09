"""Reuse a stored move for ordering while keeping history guards on its score."""
import ast


def transform(source):
    tree=ast.parse(source)
    search=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='search')
    matches=[n for n in search.body if isinstance(n,ast.If)
        and 'ttcontext[slot] == context' in ast.unparse(n.test)]
    assert len(matches)==1
    old=matches[0]
    assert ast.unparse(old.body[0])=='hint = ttdata[slot, 3]'
    assert len(old.body)==2 and isinstance(old.body[1],ast.If)
    replacement=ast.parse('''
if not quiescence and ttkey[slot] == key:
    hint = ttdata[slot, 3]
    if ttcontext[slot] == context and ttdata[slot, 4] == state[3]:
        pass
''').body[0]
    replacement.body[1].body=[old.body[1]]
    search.body[search.body.index(old)]=replacement
    ast.fix_missing_locations(tree)
    return ast.unparse(tree)+'\n'
