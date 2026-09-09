"""Exact passed-pawn classification using enemy extrema already collected per file."""
import ast


def transform(original):
    begin = original.index('def classical(')
    end = original.index('\n\n@njit(cache=False)', begin)
    block = original[begin:end]
    before = '    pawns = np.zeros((2, 8), dtype=np.int64)'
    assert block.count(before) == 1
    block = block.replace(before, '    pawns = np.zeros((4, 8), dtype=np.int64)\n'
        '    for file in range(8):\n        pawns[2, file] = 8\n        pawns[3, file] = -1', 1)
    before = '            pawns[c, sq % 16] += 1'
    assert block.count(before) == 1
    block = block.replace(before, before + '\n            if c == 0:\n'
        '                pawns[2, sq % 16] = min(pawns[2, sq % 16], sq // 16)\n'
        '            else:\n                pawns[3, sq % 16] = max(pawns[3, sq % 16], sq // 16)', 1)
    before = '''            for rr in range(rank + side, 8 if side == 1 else -1, side):
                for ff in range(max(0, f - 1), min(8, f + 2)):
                    if board[rr * 16 + ff] == -side:
                        passed = False'''
    assert block.count(before) == 1
    block = block.replace(before, '''            for ff in range(max(0, f - 1), min(8, f + 2)):
                if (side == 1 and pawns[3, ff] > rank) or (side == -1 and pawns[2, ff] < rank):
                    passed = False''', 1)
    result = original[:begin] + block + original[end:]
    def unchanged(tree):
        return [ast.dump(n) for n in tree.body if not (isinstance(n, ast.FunctionDef) and n.name == 'classical')]
    assert unchanged(ast.parse(original)) == unchanged(ast.parse(result))
    return result
