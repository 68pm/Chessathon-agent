"""Rule-aware, phase-guarded residual integration over the exact pawn-mask core."""

import ast

from scripts.overnight_check_prefilter import changed_source as with_prefilter
from scripts.overnight_geometry_trial import ROOT

HELPERS = '''
@njit(cache=False)
def legal_ep_file(board, state):
    ep, side = state[2], state[0]
    if ep < 0:
        return -1
    for delta in (-1, 1):
        source = ep - 16 * side + delta
        victim = ep - 16 * side
        if source >= 0 and not source & 0x88 and board[source] == side and board[victim] == -side:
            move = encode_move(source, ep, 0, 1)
            old = make(board, state, move)
            valid = not attacked(board, state[4 if side == 1 else 5], -side)
            unmake(board, state, move, old)
            if valid:
                return ep % 16
    return -1


@njit(cache=False)
def rule_residual(board, state, output, rule_weights, accumulator):
    c = 0 if state[0] == 1 else 1
    rights = state[1]
    own_k = int((rights & (1 if c == 0 else 4)) != 0)
    own_q = int((rights & (2 if c == 0 else 8)) != 0)
    enemy_k = int((rights & (4 if c == 0 else 1)) != 0)
    enemy_q = int((rights & (8 if c == 0 else 2)) != 0)
    ep = legal_ep_file(board, state)
    draw_clock = np.float32(min(70, state[3]) / 70.0)
    residual = 0.0
    for j in range(len(output)):
        pre = accumulator[c, j]
        pre += own_k * rule_weights[0, j] + own_q * rule_weights[1, j]
        pre += enemy_k * rule_weights[2, j] + enemy_q * rule_weights[3, j]
        if ep >= 0:
            pre += rule_weights[4 + ep, j]
        pre += draw_clock * rule_weights[12, j]
        residual += min(1.0, max(0.0, pre)) * output[j]
    return residual


@njit(cache=False)
def evaluate_accumulator(board, state, output, rule_weights, blend, conversion, accumulator):
    base, phase = classical_phase(board, state, conversion)
    if blend == 0.0 or state[6] <= 12 or phase <= 8:
        return base
    residual = rule_residual(board, state, output, rule_weights, accumulator)
    return base + int(round(blend * min(600.0, max(-600.0, residual))))


@njit(cache=False)
def classical(board, state, conversion=False):
    return classical_phase(board, state, conversion)[0]
'''


def changed_source(pawn_source):
    tree = ast.parse(pawn_source)
    original_path = ROOT / 'runs/overnight-20260909/coalesced-search-01/prototype/engine/compiled_core.py'
    restored = ast.parse(with_prefilter(original_path.read_text(encoding='utf-8')))
    neural_functions = {n.name: n for n in restored.body if isinstance(n, ast.FunctionDef)
                        and n.name in ('search', 'root_iteration')}
    for index, node in enumerate(tree.body):
        if isinstance(node, ast.FunctionDef) and node.name in neural_functions:
            tree.body[index] = neural_functions[node.name]
    for function in neural_functions.values():
        names = [a.arg for a in function.args.args]
        function.args.args.insert(names.index('output') + 1, ast.arg(arg='rule_weights'))
        for node in ast.walk(function):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
                continue
            if node.func.id in ('search', 'evaluate_accumulator'):
                index = next(i for i, arg in enumerate(node.args) if isinstance(arg, ast.Name) and arg.id == 'output')
                node.args.insert(index + 1, ast.Name(id='rule_weights', ctx=ast.Load()))
    for function in tree.body:
        if not isinstance(function, ast.FunctionDef):
            continue
        if function.name == 'make':
            old = next(n for n in function.body if isinstance(n, ast.Assign)
                       and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'old')
            assert len(old.value.elts) == 7
            old.value.elts.append(ast.parse('state[6]', mode='eval').body)
            assert isinstance(function.body[-1], ast.Return)
            function.body[-1:-1] = ast.parse('if side == -1:\n    state[6] += 1').body
        elif function.name == 'unmake':
            loop = next(n for n in function.body if isinstance(n, ast.For))
            assert ast.unparse(loop.iter) == 'range(1, 6)'
            loop.iter = ast.parse('range(1, 7)', mode='eval').body
        elif function.name == 'classical':
            function.name = 'classical_phase'
            assert isinstance(function.body[-1], ast.Return)
            function.body[-1].value = ast.Tuple(elts=[function.body[-1].value,
                ast.Name(id='phase', ctx=ast.Load())], ctx=ast.Load())
    index = next(i for i, n in enumerate(tree.body) if isinstance(n, ast.FunctionDef) and n.name == 'evaluate_accumulator')
    tree.body[index:index + 1] = ast.parse(HELPERS).body
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + '\n'


def driver_source(source):
    replacements = [
        ('square(board.king(True)), square(board.king(False))], dtype=np.int64)',
         'square(board.king(True)), square(board.king(False)), board.fullmove_number], dtype=np.int64)'),
        ('        self.output = np.zeros(32, dtype=np.float32)\n',
         '        self.output = np.zeros(32, dtype=np.float32)\n        self.rule_weights = np.zeros((13, 32), dtype=np.float32)\n'),
        ("                self.output = data['output'].astype(np.float32)\n",
         "                self.output = data['output'].astype(np.float32)\n                self.rule_weights = data['rule_weights'].astype(np.float32)\n"),
        ('assert self.weights.shape == (768, 32) and self.bias.shape == self.output.shape == (32,)',
         'assert self.weights.shape == (768, 64) and self.bias.shape == self.output.shape == (64,)\n            assert self.rule_weights.shape == (13, 64)'),
        ('(self.weights, self.bias, self.output))', '(self.weights, self.bias, self.output, self.rule_weights))'),
        ('self.weights, self.bias, self.output, self.blend, self.conversion, self.reductions)',
         'self.weights, self.bias, self.output, self.rule_weights, self.blend, self.conversion, self.reductions)')]
    for old, new in replacements:
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    return source
