"""Shared-budget defensive counterchecks and explicit root evaluation context."""

import ast


def changed_source(source):
    tree = ast.parse(source)
    search = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'search')
    tags = [n for n in search.body if isinstance(n, ast.AugAssign)
            and isinstance(n.target, ast.Name) and n.target.id == 'tt_context']
    assert len(tags) == 2 and 'state[6]' in ast.unparse(tags[-1])
    tags[-1].value = ast.parse(
        'np.uint64(min(state[6], 13) if blend != 0.0 else 0) * np.uint64(0xa0761d6478bd642f)',
        mode='eval').body
    setting = next(n for n in search.body if isinstance(n, ast.Assign)
                   and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'quiet_checks')
    assert ast.unparse(setting.value) == 'quiescence and (not checked) and (quiet_attacker == side) and (quiet_checks_left > 0)'
    # Once a near-king attack has activated the shared four-check budget, both
    # players may spend those credits. No extra budget, unbounded checks or
    # nonchecking quiet move is admitted.
    setting.value = ast.parse(
        'quiescence and not checked and quiet_attacker != 0 and quiet_checks_left > 0',
        mode='eval').body
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + '\n'


def driver_source(source):
    old = '        pieces, state = arrays(board)\n'
    assert source.count(old) == 1
    source = source.replace(old, old + '        effective_blend = self.blend if board.fullmove_number > 12 else 0.0\n')
    old = 'self.output, self.rule_weights, self.blend, self.conversion, self.reductions)'
    assert source.count(old) == 1
    return source.replace(old, 'self.output, self.rule_weights, effective_blend, self.conversion, self.reductions)')
