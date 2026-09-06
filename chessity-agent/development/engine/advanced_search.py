"""Original PVS experiment with targeted quiescence move generation.

This reuses the project's board/history/deadline machinery. It imports no external
engine implementation. The first experiment preserves full-depth minimax semantics.
"""

import chess

from engine.move_ordering import ordered
from engine.search import Search as BaseSearch
from engine.search import position_key
from engine.transposition import EXACT, LOWER, MATE, UPPER, pack_score, unpack_score


def tactical_moves(board):
    """All legal captures plus every legal quiet promotion, including underpromotions."""
    moves = list(board.generate_legal_captures())
    penultimate = chess.BB_RANK_7 if board.turn else chess.BB_RANK_2
    last = chess.BB_RANK_8 if board.turn else chess.BB_RANK_1
    promoting_pawns = board.pawns & board.occupied_co[board.turn] & penultimate
    if promoting_pawns:
        moves.extend(move for move in board.generate_legal_moves(from_mask=promoting_pawns, to_mask=last)
                     if move.promotion and not board.is_capture(move))
    return moves


class Search(BaseSearch):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.scout_searches = 0
        self.full_researches = 0

    def qsearch(self, board, alpha, beta, ply, qdepth=0):
        self.tick()
        checked = board.is_check()
        if checked:
            moves = list(board.legal_moves)
            terminal = self.terminal(board, ply, moves)
            if terminal is not None:
                return terminal
        else:
            # Non-check draws all have score zero; checkmate was handled above.
            if board.halfmove_clock >= 100 or board.is_insufficient_material() or self.counts[position_key(board)] >= 3:
                return 0
            # A single legal move rules out stalemate. Do not enumerate every quiet move.
            if next(board.generate_legal_moves(), None) is None:
                return 0
        if ply >= 100 or (qdepth >= 12 and not checked):
            return self.evaluate(board)
        if not checked:
            stand = self.evaluate(board)
            if stand >= beta:
                return stand
            alpha = max(alpha, stand)
            moves = tactical_moves(board)
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
        key = (position_key(board), board.halfmove_clock, frozenset(self.counts.items()))
        entry = self.table.get(key)
        original_alpha = alpha
        if entry is not None and entry.depth >= depth:
            value = unpack_score(entry.score, ply)
            if entry.bound == EXACT or (entry.bound == LOWER and value >= beta) or (entry.bound == UPPER and value <= alpha):
                return value
        best, best_move = -MATE - 1, None
        ranked = ordered(board, moves, entry.move if entry else None, self.killers[ply], self.history)
        for index, move in enumerate(ranked):
            quiet = not board.is_capture(move) and not move.promotion
            if index == 0:
                value = -self.child(board, move, self.negamax, depth - 1, -beta, -alpha, ply + 1)
            else:
                self.scout_searches += 1
                value = -self.child(board, move, self.negamax, depth - 1, -alpha - 1, -alpha, ply + 1)
                if alpha < value < beta:
                    self.full_researches += 1
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
