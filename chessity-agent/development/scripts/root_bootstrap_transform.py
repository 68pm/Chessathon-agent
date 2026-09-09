"""Bounded root ordering seed and valid completed-child fallback."""


def core_source(source):
    start = source.index('def root_iteration(')
    prefix, root = source[:start], source[start:]
    old = 'blend, conversion, reductions):'
    assert root.count(old) == 1
    root = root.replace(old, 'blend, conversion, reductions, root_quiet_checks):')
    old = 'np.int64(2), np.int64(4), np.int64(0))'
    assert root.count(old) == 1
    root = root.replace(old, 'np.int64(2), np.int64(root_quiet_checks), np.int64(0))')
    assert root.count('return (previous, 0, False)') == 1
    return prefix + root.replace('return (previous, 0, False)', 'return (bestmove, best, False)')


def driver_source(source):
    anchor = '        previous = int(root[0])\n'
    assert source.count(anchor) == 1
    seed = '''        # A seed is not a completed full four-credit depth. Its work shares the
        # original move clock and total node allowance with normal search.
        bootstrap_deadline = min(deadline, started + min(.025, max(0., seconds) * .05))
        # During warmup the external initialization watchdog is the deadline.
        if seconds == float('inf'):
            bootstrap_deadline = deadline
        control[2] = min(max_nodes, 4096)
        if time.perf_counter() < bootstrap_deadline:
            move, score, _ = core.root_iteration(
                pieces, state, 1, previous, root, bonuses, hashes, len(past), self.ttkey,
                self.ttcontext, self.ttdata, self.killers, self.history, control, bootstrap_deadline,
                self.weights, self.bias, self.output, self.blend, self.conversion, self.reductions, np.int64(0))
            if score > -31000:
                previous = int(move)
                result = Result(decode(previous), int(score), 0)
        control[1], control[2] = 0, max_nodes
'''
    source = source.replace(anchor, anchor + seed)
    old = '            if time.perf_counter() >= soft_deadline:\n'
    assert source.count(old) == 1
    source = source.replace(old, '            if time.perf_counter() >= soft_deadline or control[0] >= max_nodes:\n')
    old = 'self.weights, self.bias, self.output, self.blend, self.conversion, self.reductions)'
    assert source.count(old) == 1
    source = source.replace(old, 'self.weights, self.bias, self.output, self.blend, self.conversion, self.reductions, np.int64(4))')
    old = '            if not completed:\n                break\n'
    assert source.count(old) == 1
    source = source.replace(old, '''            if not completed:
                if result.depth == 0 and score > -31000:
                    result = Result(decode(int(move)), int(score), 0)
                break
''')
    return source
