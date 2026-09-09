"""Small symmetric position features and a bounded, original residual fit."""
import itertools
import chess
import numpy as np

CAPS = np.array([25., 1., 1.])


def features(board):
    phase = min(24, sum(len(board.pieces(p, c)) * w
        for p, w in ((2, 1), (3, 1), (4, 2), (5, 4)) for c in (True, False)))
    result = np.zeros(3)
    for colour in (True, False):
        sign = 1 if colour == board.turn else -1
        king = board.king(colour)
        king_file, king_rank = chess.square_file(king), chess.square_rank(king)
        forward = 1 if colour else -1
        if board.pieces(chess.QUEEN, not colour):
            for file in range(max(0, king_file - 1), min(8, king_file + 2)):
                distances = [(chess.square_rank(p) - king_rank) * forward
                    for p in board.pieces(chess.PAWN, colour) if chess.square_file(p) == file
                    and (chess.square_rank(p) - king_rank) * forward > 0]
                gap = min(3, max(0, min(distances, default=4) - 1))
                result[0] -= sign * gap * phase / 24
        pawn_attacks = set()
        for pawn in board.pieces(chess.PAWN, not colour):
            pawn_attacks.update(board.attacks(pawn))
        for p in (2, 3, 4, 5):
            unsafe = sum(target in pawn_attacks and board.color_at(target) != colour
                for origin in board.pieces(p, colour) for target in board.attacks(origin))
            result[1] -= sign * unsafe * (3 if p in (2, 3) else 1) * phase / 24
            result[2] -= sign * unsafe * 2 * (24 - phase) / 24
    return result * CAPS


def solve_box(x, y, weights, penalty=2000.):
    """Exact active-set solution of a three-variable convex box-constrained fit."""
    x, y, weights = np.asarray(x), np.asarray(y), np.asarray(weights)
    assert x.shape == (len(y), 3) and weights.shape == y.shape
    assert np.isfinite(x).all() and np.isfinite(y).all() and np.all(weights > 0)
    gram = x.T @ (x * weights[:, None]) + np.eye(3) * penalty
    rhs = x.T @ (weights * y)
    best = None
    for state in itertools.product(('free', 'zero', 'one'), repeat=3):
        free = [i for i, value in enumerate(state) if value == 'free']
        fixed = [i for i in range(3) if i not in free]
        coefficient = np.array([float(value == 'one') for value in state])
        if free:
            coefficient[free] = np.linalg.solve(gram[np.ix_(free, free)],
                rhs[free] - gram[np.ix_(free, fixed)] @ coefficient[fixed])
        if np.any(coefficient < -1e-9) or np.any(coefficient > 1 + 1e-9):
            continue
        coefficient = np.clip(coefficient, 0, 1)
        objective = float(coefficient @ gram @ coefficient - 2 * coefficient @ rhs)
        if best is None or objective < best[0]:
            best = objective, coefficient
    return best[1]


def predict(x, coefficient):
    return np.asarray(x) @ np.asarray(coefficient)
