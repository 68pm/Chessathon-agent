"""Probe later root moves with a narrow window, verifying every improvement."""


def transform(source):
    old = '''        value = -search(board, state, depth - 1, -31000, -cutoff, 1, 0, hashes, hlen + 1, ctx, ttkey, ttcontext, ttdata, killers, history, control, deadline, weights, bias, output, blend, conversion, reductions, accumulator, move_storage, score_storage)'''
    assert source.count(old) == 1
    new = '''        # A later move only needs to disprove the incumbent before a full search.
        if index == 0:
            value = -search(board, state, depth - 1, -31000, 31000, 1, 0, hashes, hlen + 1, ctx, ttkey, ttcontext, ttdata, killers, history, control, deadline, weights, bias, output, blend, conversion, reductions, accumulator, move_storage, score_storage)
        else:
            value = -search(board, state, depth - 1, -cutoff - 1, -cutoff, 1, 0, hashes, hlen + 1, ctx, ttkey, ttcontext, ttdata, killers, history, control, deadline, weights, bias, output, blend, conversion, reductions, accumulator, move_storage, score_storage)
            if value > cutoff and (not control[1]):
                value = -search(board, state, depth - 1, -31000, -cutoff, 1, 0, hashes, hlen + 1, ctx, ttkey, ttcontext, ttdata, killers, history, control, deadline, weights, bias, output, blend, conversion, reductions, accumulator, move_storage, score_storage)'''
    return source.replace(old, new)
