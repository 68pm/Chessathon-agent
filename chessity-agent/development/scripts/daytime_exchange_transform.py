"""Original bounded on-square exchange ordering; never a move-pruning rule."""
import ast

HELPERS = '''
@njit(cache=False)
def recapture_candidate(board, state, target):
    side = state[0]
    sources = np.empty(32, dtype=np.int64)
    count = 0
    for delta in (-1, 1):
        source = target - 16 * side + delta
        if source >= 0 and not source & 0x88 and board[source] == side:
            sources[count], count = source, count + 1
    for delta in KNIGHT:
        source = target + delta
        if source >= 0 and not source & 0x88 and board[source] == 2 * side:
            sources[count], count = source, count + 1
    for delta in KING:
        source = target + delta
        if source >= 0 and not source & 0x88 and board[source] == 6 * side:
            sources[count], count = source, count + 1
        source = target + delta
        while source >= 0 and not source & 0x88:
            piece = board[source]
            if piece:
                diagonal = delta in (-17, -15, 15, 17)
                if piece * side > 0 and (abs(piece) == 5 or abs(piece) == (3 if diagonal else 4)):
                    sources[count], count = source, count + 1
                break
            source += delta
    chosen, cheapest = 0, 31000
    for index in range(count):
        source = sources[index]
        piece = abs(board[source])
        cost = 30000 if piece == 6 else MG[piece]
        if cost >= cheapest:
            continue
        promotion = 5 if piece == 1 and target // 16 in (0, 7) else 0
        move = encode_move(source, target, promotion)
        old = make(board, state, move)
        legal = not attacked(board, state[4 if side == 1 else 5], -side)
        unmake(board, state, move, old)
        if legal:
            chosen, cheapest = move, cost
    return chosen


@njit(cache=False)
def bounded_exchange(board, state, move):
    """Six recaptures maximum; an uncertain continuation keeps original priority."""
    side = state[0]
    target, flags, promotion = (move >> 7) & 127, move >> 17, (move >> 14) & 7
    if promotion or flags & 1 or not board[target] or attacked(board, state[4 if side == 1 else 5], -side):
        return 0
    gain = np.zeros(7, dtype=np.int64)
    gain[0] = MG[abs(board[target])]
    initial = make(board, state, move)
    protected = (attacked(board, state[4 if side == 1 else 5], -side)
                 or attacked(board, state[4 if side == -1 else 5], side))
    if protected:
        unmake(board, state, move, initial)
        return 0
    moves = np.zeros(6, dtype=np.int64)
    old_states = np.zeros((6, 7), dtype=np.int64)
    count, uncertain = 0, False
    while count < 6 and abs(board[target]) != 6:
        recapture = recapture_candidate(board, state, target)
        if not recapture:
            break
        promo = (recapture >> 14) & 7
        gain[count + 1] = MG[abs(board[target])] + (MG[promo] - MG[1] if promo else 0) - gain[count]
        old = make(board, state, recapture)
        moves[count] = recapture
        for j in range(7):
            old_states[count, j] = old[j]
        count += 1
    if count == 6 and abs(board[target]) != 6:
        uncertain = bool(recapture_candidate(board, state, target))
    for i in range(count - 1, -1, -1):
        unmake(board, state, moves[i], old_states[i])
    unmake(board, state, move, initial)
    for i in range(count, 0, -1):
        gain[i - 1] = min(gain[i - 1], -gain[i])
    return 0 if uncertain else gain[0]


'''


def transform(original):
    marker = '@njit(cache=False)\ndef order_moves('
    assert original.count(marker) == 1
    source = original.replace(marker, HELPERS + marker, 1)
    old = 'def order_moves(board, moves, hint, killers, history, ply, side):'
    assert source.count(old) == 1
    source = source.replace(old, 'def order_moves(board, moves, hint, killers, history, ply, side, state, exchange=False):', 1)
    start = source.index('def order_moves(')
    end = source.index('\n\n@njit(cache=False)', start)
    order = source[start:end]
    marker = '        elif move == killers[ply, 0]:'
    assert order.count(marker) == 1
    order = order.replace(marker, '''            if exchange and captured and not promo and MG[abs(board[source])] > MG[captured]:
                estimate = bounded_exchange(board, state, move)
                if estimate < 0:
                    scores[i] = -100000 + estimate
''' + marker, 1)
    source = source[:start] + order + source[end:]
    source = source.replace('order_moves(board, moves, hint, killers, history, ply, side)',
        'order_moves(board, moves, hint, killers, history, ply, side, state, depth >= 3 and ply <= 1 and not checked)', 1)
    source = source.replace('order_moves(board, moves, previous, killers, history, 0, state[0])',
        'order_moves(board, moves, previous, killers, history, 0, state[0], state, depth >= 3)', 1)
    allowed = {'recapture_candidate', 'bounded_exchange', 'order_moves', 'search', 'root_iteration'}
    def untouched(tree):
        return [ast.dump(n) for n in tree.body if not (isinstance(n, ast.FunctionDef) and n.name in allowed)]
    assert untouched(ast.parse(original)) == untouched(ast.parse(source))
    return source
