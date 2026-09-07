"""Exact selected41 root wrapper; shared unchanged search avoids dual JIT loading."""
import numpy as np
from numba import njit

from experiments.aspiration_core import (
    build_accumulator,
    make,
    order_moves,
    position_hash,
    search,
    unmake,
    update_accumulator,
)


@njit(cache=False)
def root_iteration(board, state, depth, previous, moves, bonuses, hashes, hlen,
                   ttkey, ttcontext, ttdata, killers, history, control, deadline,
                   weights, bias, output, blend, conversion, reductions):
    accumulator = build_accumulator(board, weights, bias)
    context = np.uint64(0)
    for i in range(max(0, hlen - state[3] - 1), hlen):
        context += hashes[i]
    order = order_moves(board, moves, previous, killers, history, 0, state[0])
    best, bestmove = -31000, previous
    for index in range(len(moves)):
        choice = index
        for k in range(index + 1, len(moves)):
            if order[k] > order[choice]:
                choice = k
        move, bonus = moves[choice], bonuses[choice]
        moves[choice], moves[index] = moves[index], moves[choice]
        bonuses[choice], bonuses[index] = bonuses[index], bonuses[choice]
        order[choice], order[index] = order[index], order[choice]
        old = make(board, state, move)
        if blend != 0.0:
            update_accumulator(accumulator, weights, move, old, 1)
        key = position_hash(board, state)
        hashes[hlen] = key
        ctx = key if state[3] == 0 or state[1] != old[2] else context + key
        cutoff = best if abs(best) >= 29000 else best - bonus
        value = -search(board, state, depth - 1, -31000, -cutoff, 1, 0,
                        hashes, hlen + 1, ctx, ttkey, ttcontext, ttdata, killers, history,
                        control, deadline, weights, bias, output, blend, conversion, reductions, accumulator)
        if blend != 0.0:
            update_accumulator(accumulator, weights, move, old, -1)
        unmake(board, state, move, old)
        if control[1]:
            return previous, 0, False
        if abs(value) < 29000:
            value += bonus
        if value > best:
            best, bestmove = value, move
    return bestmove, best, True
