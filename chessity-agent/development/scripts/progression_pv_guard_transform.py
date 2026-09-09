"""Keep full depth for late quiet moves in a principal-variation window."""
def transform(source):
    old = '        reduced = reductions and (not quiescence) and (depth >= 3) and (legal_count >= 5) and quiet and (not checked) and (not attacked(board, state[4 if state[0] == 1 else 5], side))'
    assert source.count(old) == 1
    return source.replace(old, old + ' and (beta - alpha <= 1)')
