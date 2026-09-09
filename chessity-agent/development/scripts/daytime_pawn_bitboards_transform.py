"""Exact per-evaluation scalar pawn masks, without modifying make/unmake or search."""
import ast

HELPERS = "\nPAWN_FILES = np.zeros(8, dtype=np.uint64)\nPASSED_PAWN_MASKS = np.zeros((2, 128), dtype=np.uint64)\nfor _file in range(8):\n    PAWN_FILES[_file] = np.uint64(0x0101010101010101 << _file)\nfor _colour in range(2):\n    for _square in range(128):\n        if _square & 0x88:\n            continue\n        _rank, _file = _square // 16, _square % 16\n        _mask = 0\n        for _ahead in (range(_rank + 1, 8) if _colour == 0 else range(_rank)):\n            for _adjacent in range(max(0, _file - 1), min(8, _file + 2)):\n                _mask |= 1 << (8 * _ahead + _adjacent)\n        PASSED_PAWN_MASKS[_colour, _square] = np.uint64(_mask)\n\n\n@njit(cache=False, inline='always')\ndef pawn_file_count(pawns, file):\n    mask = pawns & PAWN_FILES[file]\n    if mask == 0:\n        return 0\n    return 1 + int((mask & (mask - np.uint64(1))) != 0)\n"


def transform(source):
    tree = ast.parse(source)
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'classical')
    setup = next(n for n in function.body if isinstance(n, ast.For)
                 and isinstance(n.target, ast.Name) and n.target.id == 'file')
    function.body.remove(setup)
    assignments = {n.targets[0].id: n for n in function.body if isinstance(n, ast.Assign)
                   and isinstance(n.targets[0], ast.Name)}
    for name, replacement in [('pawns', 'white_pawns = np.uint64(0)\nblack_pawns = np.uint64(0)'),
        ('bishops', 'white_bishops, black_bishops = 0, 0'),
        ('material', 'white_material, black_material = 0, 0')]:
        node = assignments[name]
        assert isinstance(node.value, ast.Call)
        index = function.body.index(node)
        function.body[index:index + 1] = ast.parse(replacement).body
    loops = [n for n in function.body if isinstance(n, ast.For)]
    assert len(loops) == 2
    first = loops[0]
    pawn = next(n for n in first.body if isinstance(n, ast.If) and ast.unparse(n.test) == 'p == 1')
    pawn.body = ast.parse('''
if c == 0:
    white_pawns |= np.uint64(1) << np.uint64(sq // 16 * 8 + sq % 16)
else:
    black_pawns |= np.uint64(1) << np.uint64(sq // 16 * 8 + sq % 16)
''').body

    class Counters(ast.NodeTransformer):
        def visit_AugAssign(self, node):
            if isinstance(node.target, ast.Subscript) and isinstance(node.target.value, ast.Name):
                name = node.target.value.id
                assert name in ('bishops', 'material')
                return ast.parse(f'if c == 0:\n    white_{name} += {ast.unparse(node.value)}\nelse:\n    black_{name} += {ast.unparse(node.value)}').body[0]
            return self.generic_visit(node)

    Counters().visit(first)
    pawn = next(n for n in loops[1].body if isinstance(n, ast.If) and ast.unparse(n.test) == 'p == 1'
        and any(isinstance(c, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'passed'
            for t in c.targets) for c in n.body))
    index = next(i for i, n in enumerate(pawn.body) if isinstance(n, ast.Assign)
        and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'passed')
    assert isinstance(pawn.body[index + 1], ast.For)
    pawn.body[index:index + 2] = ast.parse('passed = ((black_pawns if c == 0 else white_pawns) & PASSED_PAWN_MASKS[c, sq]) == 0').body

    class Reads(ast.NodeTransformer):
        def visit_Call(self, node):
            if isinstance(node.func, ast.Name) and node.func.id == 'max' and len(node.args) == 1 and isinstance(node.args[0], ast.Name) and node.args[0].id == 'material':
                node.args = [ast.Name(id=name, ctx=ast.Load()) for name in ('white_material', 'black_material')]
            return self.generic_visit(node)

        def visit_Subscript(self, node):
            if isinstance(node.value, ast.Name) and node.value.id == 'pawns':
                colour, file = node.slice.elts
                return ast.parse(f'pawn_file_count(white_pawns if {ast.unparse(colour)} == 0 else black_pawns, {ast.unparse(file)})', mode='eval').body
            if isinstance(node.value, ast.Name) and node.value.id in ('bishops', 'material'):
                assert isinstance(node.slice, ast.Constant) and node.slice.value in (0, 1)
                return ast.Name(id=('white_' if node.slice.value == 0 else 'black_') + node.value.id, ctx=node.ctx)
            return self.generic_visit(node)

    Reads().visit(function)
    assert not any(isinstance(n, ast.Name) and n.id in ('pawns', 'bishops', 'material') for n in ast.walk(function))
    index = tree.body.index(function)
    tree.body[index:index] = ast.parse(HELPERS).body
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + '\n'
