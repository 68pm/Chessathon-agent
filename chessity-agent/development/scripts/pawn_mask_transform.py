"""Exact classical pawn queries using the maintained piece masks."""

import ast

from scripts.overnight_combined_search import changed_source as combined

HELPERS = '''
PAWN_FILES = np.zeros(8, dtype=np.uint64)
PASSED_PAWN_MASKS = np.zeros((2, 128), dtype=np.uint64)
for _file in range(8):
    PAWN_FILES[_file] = np.uint64(0x0101010101010101 << _file)
for _colour in range(2):
    for _square in range(128):
        if _square & 0x88:
            continue
        _rank, _file = _square // 16, _square % 16
        _mask = 0
        for _ahead in (range(_rank + 1, 8) if _colour == 0 else range(_rank)):
            for _adjacent in range(max(0, _file - 1), min(8, _file + 2)):
                _mask |= 1 << (8 * _ahead + _adjacent)
        PASSED_PAWN_MASKS[_colour, _square] = np.uint64(_mask)


@njit(cache=False, inline='always')
def pawn_file_count(pawns, file):
    mask = pawns & PAWN_FILES[file]
    if mask == 0:
        return 0
    return 1 + int((mask & (mask - np.uint64(1))) != 0)
'''


def changed_source(original):
    tree = ast.parse(combined(original))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'classical')
    assignments = {n.targets[0].id: n for n in function.body if isinstance(n, ast.Assign)
                   and isinstance(n.targets[0], ast.Name)}
    for name, replacement in (
            ('pawns', 'pawn_masks = (np.uint64(board[135]), np.uint64(board[133]))'),
            ('bishops', 'white_bishops, black_bishops = 0, 0'),
            ('material', 'white_material, black_material = 0, 0')):
        assert isinstance(assignments[name].value, ast.Call)
        index = function.body.index(assignments[name])
        function.body[index:index + 1] = ast.parse(replacement).body
    loops = [n for n in function.body if isinstance(n, ast.For)]
    assert len(loops) == 2
    first = loops[0]
    pawn_update = next(n for n in first.body if isinstance(n, ast.If)
                       and ast.unparse(n.test) == 'p == 1')
    first.body.remove(pawn_update)
    for node in ast.walk(first):
        if isinstance(node, ast.AugAssign) and isinstance(node.target, ast.Subscript):
            name = node.target.value.id
            assert name in ('bishops', 'material')
            replacement = ast.parse(f'if c == 0:\n    white_{name} += {ast.unparse(node.value)}\nelse:\n    black_{name} += {ast.unparse(node.value)}').body[0]
            for container in ast.walk(first):
                for _, value in ast.iter_fields(container):
                    if isinstance(value, list) and node in value:
                        value[value.index(node)] = replacement
                        break
    pawn_branch = next(n for n in loops[1].body if isinstance(n, ast.If)
                       and ast.unparse(n.test) == 'p == 1' and any(
                           isinstance(c, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'passed' for t in c.targets)
                           for c in n.body))
    index = next(i for i, n in enumerate(pawn_branch.body) if isinstance(n, ast.Assign)
                 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'passed')
    assert isinstance(pawn_branch.body[index + 1], ast.For)
    pawn_branch.body[index:index + 2] = ast.parse('passed = (pawn_masks[enemy] & PASSED_PAWN_MASKS[c, sq]) == 0').body

    class Reads(ast.NodeTransformer):
        def visit_Call(self, node):
            if (isinstance(node.func, ast.Name) and node.func.id == 'max' and len(node.args) == 1
                    and isinstance(node.args[0], ast.Name) and node.args[0].id == 'material'):
                node.args = [ast.Name(id=name, ctx=ast.Load()) for name in ('white_material', 'black_material')]
            return self.generic_visit(node)

        def visit_Subscript(self, node):
            if isinstance(node.value, ast.Name) and node.value.id == 'pawns':
                colour, file = node.slice.elts
                return ast.Call(func=ast.Name(id='pawn_file_count', ctx=ast.Load()), args=[
                    ast.Subscript(value=ast.Name(id='pawn_masks', ctx=ast.Load()), slice=colour, ctx=ast.Load()), file], keywords=[])
            if isinstance(node.value, ast.Name) and node.value.id in ('bishops', 'material'):
                assert isinstance(node.slice, ast.Constant) and node.slice.value in (0, 1)
                prefix = 'white_' if node.slice.value == 0 else 'black_'
                return ast.Name(id=prefix + node.value.id, ctx=node.ctx)
            return self.generic_visit(node)

    Reads().visit(function)
    assert not any(isinstance(n, ast.Name) and n.id in ('pawns', 'bishops', 'material') for n in ast.walk(function))
    tree.body[tree.body.index(function):tree.body.index(function)] = ast.parse(HELPERS).body
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + '\n'
