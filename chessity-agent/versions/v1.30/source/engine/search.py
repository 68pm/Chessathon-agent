"""Iterative deepening negamax and capture/evasion quiescence, independently implemented."""

import time
from collections import Counter
from dataclasses import dataclass

from engine.evaluation import Evaluator, classical, phase, style_score
from engine.move_ordering import ordered
from engine.transposition import EXACT, LOWER, MATE, UPPER, Table, pack_score, unpack_score


class SearchTimeout(Exception):
    pass


def position_key(board):
    # python-chess 1.11.2 is pinned; this includes legally relevant en passant/castling.
    return board._transposition_key()


@dataclass
class Result:
    move: object
    score: int = 0
    depth: int = 0
    nodes: int = 0
    elapsed: float = 0
    style: int = 0


class Search:
    def __init__(self, evaluator=None, style_tolerance=0, player_policy=None, policy_cp=20):
        self.evaluate = evaluator or Evaluator()
        self.style_tolerance = style_tolerance
        self.player_policy = player_policy
        self.policy_cp = max(0, min(25, policy_cp))
        self.table = Table()
        self.history = {}
        self.killers = [[] for _ in range(128)]

    def tick(self):
        self.nodes += 1
        if time.perf_counter() >= self.deadline:
            raise SearchTimeout

    def terminal(self, board, ply, moves):
        if not moves:
            return -MATE + ply if board.is_check() else 0
        if board.halfmove_clock >= 100 or board.is_insufficient_material():
            return 0
        if self.counts[position_key(board)] >= 3:
            return 0
        return None

    def child(self, board, move, fn, *args):
        board.push(move)
        key = position_key(board)
        self.counts[key] += 1
        try:
            return fn(board, *args)
        finally:
            self.counts[key] -= 1
            if not self.counts[key]:
                del self.counts[key]
            board.pop()

    def qsearch(self, board, alpha, beta, ply, qdepth=0):
        self.tick()
        moves = list(board.legal_moves)
        terminal = self.terminal(board, ply, moves)
        if terminal is not None:
            return terminal
        checked = board.is_check()
        # Safety bound. Terminal recognition always precedes the static fallback.
        if ply >= 100 or (qdepth >= 12 and not checked):
            return self.evaluate(board)
        if not checked:
            stand = self.evaluate(board)
            if stand >= beta:
                return stand
            alpha = max(alpha, stand)
            moves = [m for m in moves if board.is_capture(m) or m.promotion]
        for move in ordered(board, moves, None, [], self.history):
            value = -self.child(board, move, self.qsearch, -beta, -alpha, ply + 1, qdepth + 1)
            if value >= beta:
                return value
            alpha = max(alpha, value)
        return alpha

    def negamax(self, board, depth, alpha, beta, ply):
        if depth <= 0:
            return self.qsearch(board, alpha, beta, ply)
        self.tick()
        moves = list(board.legal_moves)
        terminal = self.terminal(board, ply, moves)
        if terminal is not None:
            return terminal
        if ply >= 100:
            return self.evaluate(board)
        # Full repetition context avoids using a score proved under a different history.
        key = (position_key(board), board.halfmove_clock, frozenset(self.counts.items()))
        entry = self.table.get(key)
        original_alpha = alpha
        if entry is not None and entry.depth >= depth:
            value = unpack_score(entry.score, ply)
            if (
                entry.bound == EXACT
                or (entry.bound == LOWER and value >= beta)
                or (entry.bound == UPPER and value <= alpha)
            ):
                return value
        best, best_move = -MATE - 1, None
        for move in ordered(
            board, moves, entry.move if entry else None, self.killers[ply], self.history
        ):
            quiet = not board.is_capture(move) and not move.promotion
            value = -self.child(board, move, self.negamax, depth - 1, -beta, -alpha, ply + 1)
            if value > best:
                best, best_move = value, move
            alpha = max(alpha, value)
            if alpha >= beta:
                if quiet:
                    if move not in self.killers[ply]:
                        self.killers[ply] = [move] + self.killers[ply][:1]
                    hkey = (board.turn, move.from_square, move.to_square)
                    self.history[hkey] = min(100000, self.history.get(hkey, 0) + depth * depth)
                break
        bound = UPPER if best <= original_alpha else LOWER if best >= beta else EXACT
        self.table.put(key, depth, pack_score(best, ply), bound, best_move)
        return best

    def run(
        self,
        board,
        seconds=0.1,
        soft=None,
        max_depth=64,
        known=None,
        preferred_move=None,
        preference_cp=0,
    ):
        start = time.perf_counter()
        self.deadline = start + max(0, seconds)
        self.nodes = 0
        self.counts = Counter(known or {})
        key = position_key(board)
        if not self.counts[key]:
            self.counts[key] = 1
        moves = list(board.legal_moves)
        if not moves:
            return Result(None, -MATE if board.is_check() else 0)
        result = Result(moves[0])
        if seconds <= 0:
            return result
        if self.terminal(board, 0, moves) is not None:
            return result
        soft_deadline = start + (seconds if soft is None else soft)
        style_enabled = (
            self.style_tolerance > 0
            and seconds >= 0.05
            and abs(classical(board)) < 300
            and phase(board) > 0.20
            and not board.is_check()
        )
        bonuses = {}
        preference_enabled = (
            seconds >= 0.05
            and abs(classical(board)) < 300
            and phase(board) > 0.20
            and not board.is_check()
        )
        if preference_enabled and self.player_policy is not None:
            bonuses = self.player_policy.bonuses(board, moves, self.policy_cp)
        if preference_enabled and preferred_move in moves:
            # Opening preparation competes with every legal alternative. The bounded
            # root bonus never substitutes a book move for search or changes mate scores.
            bonuses[preferred_move] = bonuses.get(preferred_move, 0) + max(
                0, min(25, int(preference_cp))
            )
        try:
            for depth in range(1, max_depth + 1):
                if time.perf_counter() >= soft_deadline:
                    break
                best, chosen, alpha = -MATE - 1, result.move, -MATE - 1
                scores = []
                for move in ordered(board, moves, result.move, [], self.history):
                    self.tick()
                    bonus = bonuses.get(move, 0)
                    cutoff = alpha if abs(alpha) >= 29000 else alpha - bonus
                    value = -self.child(board, move, self.negamax, depth - 1, -MATE - 1, -cutoff, 1)
                    if abs(value) < 29000:
                        value += bonus
                    exact = value > alpha
                    # A failed-low result is only an upper bound. Re-search near ties.
                    if style_enabled and not exact and value >= alpha - self.style_tolerance:
                        value = -self.child(
                            board, move, self.negamax, depth - 1, -MATE - 1, MATE + 1, 1
                        )
                        if abs(value) < 29000:
                            value += bonus
                        exact = True
                    scores.append((move, value, exact))
                    if value > best:
                        best, chosen = value, move
                    alpha = max(alpha, value)
                if style_enabled and abs(best) < 29000:
                    eligible = [
                        m for m, v, exact in scores if exact and v >= best - self.style_tolerance
                    ]
                    chosen = max(eligible, key=lambda m: style_score(board, m))
                result = Result(
                    chosen,
                    best,
                    depth,
                    self.nodes,
                    time.perf_counter() - start,
                    style_score(board, chosen),
                )
                if abs(best) >= MATE - 100:
                    break
        except SearchTimeout:
            pass
        result.nodes, result.elapsed = self.nodes, time.perf_counter() - start
        return result
