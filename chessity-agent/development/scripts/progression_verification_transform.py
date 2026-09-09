"""Use remaining clock reserve to compare three candidates one ply deeper."""


def core_transform(source):
    old = '    best, bestmove = (-31000, previous)'
    assert source.count(old) == 1
    source = source.replace(old, old + '\n    move_scores = np.full(len(moves), -31000, dtype=np.int64)')
    assert source.count('            return (previous, 0, False)') == 1
    source = source.replace('            return (previous, 0, False)', '            return (previous, 0, False, move_scores)')
    old = '        if value > best:\n            best, bestmove = (value, move)\n    return (bestmove, best, True)'
    new = '        move_scores[index] = value\n' + old.replace('return (bestmove, best, True)', 'return (bestmove, best, True, move_scores)')
    assert source.count(old) == 1
    return source.replace(old, new)


def driver_transform(source):
    changes = {
        '    elapsed: float = 0.0': '    elapsed: float = 0.0\n    verified_depth: int = 0',
        '        previous = int(root[0])': '        previous = int(root[0])\n        verification_moves, verification_bonuses = None, None',
        '            move, score, completed = core.root_iteration(': '            move, score, completed, move_scores = core.root_iteration(',
        '            result = Result(decode(previous), int(score), depth)':
            '''            result = Result(decode(previous), int(score), depth)
            # These are search bounds, not independent value labels or a complete MultiPV ranking.
            ranked = np.argsort(-move_scores, kind='stable')[:3]
            verification_moves, verification_bonuses = root[ranked].copy(), bonuses[ranked].copy()
            assert previous in verification_moves''',
        '        result.nodes, result.elapsed = int(control[0]), time.perf_counter() - started':
            '''        # Preserve the completed full-root result if the bounded comparison runs out of time.
        if (verification_moves is not None and len(verification_moves) >= 2 and 3 <= result.depth < max_depth
                and abs(result.score) < 29000 and not control[1] and deadline - time.perf_counter() >= .05):
            move, score, completed, _ = core.root_iteration(
                pieces, state, result.depth + 1, previous, verification_moves, verification_bonuses,
                hashes, len(past), self.ttkey, self.ttcontext, self.ttdata, self.killers,
                self.history, control, deadline, self.weights, self.bias, self.output,
                self.blend, self.conversion, self.reductions, self.move_storage, self.score_storage)
            if completed:
                result.move, result.score = decode(int(move)), int(score)
                result.verified_depth = result.depth + 1
        result.nodes, result.elapsed = int(control[0]), time.perf_counter() - started''',
    }
    for old, new in changes.items():
        assert source.count(old) == 1, old
        source = source.replace(old, new)
    return source
