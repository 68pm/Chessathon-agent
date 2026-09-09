"""Python interface and clock management for our compiled core."""

import time
from dataclasses import dataclass

import chess
import numpy as np

from . import overnight_countercheck_leaf_core as core


def arrays(board):
    pieces = np.zeros(142, dtype=np.int64)
    for sq, piece in board.piece_map().items():
        pieces[(sq // 8) * 16 + sq % 8] = piece.piece_type * (1 if piece.color else -1)
    core.rebuild_metadata(pieces)
    rights = (int(board.has_kingside_castling_rights(True))
              + 2 * int(board.has_queenside_castling_rights(True))
              + 4 * int(board.has_kingside_castling_rights(False))
              + 8 * int(board.has_queenside_castling_rights(False)))
    def square(s):
        return (s // 8) * 16 + s % 8 if s is not None else -1
    state = np.array([1 if board.turn else -1, rights, square(board.ep_square), board.halfmove_clock,
                      square(board.king(True)), square(board.king(False)), board.fullmove_number], dtype=np.int64)
    return pieces, state


def decode(move):
    a, b = move & 127, (move >> 7) & 127
    return chess.Move((a // 16) * 8 + a % 16, (b // 16) * 8 + b % 16, ((move >> 14) & 7) or None)


@dataclass
class Result:
    move: object
    score: int = 0
    depth: int = 0
    nodes: int = 0
    elapsed: float = 0.0


class CompiledSearch:
    def __init__(self, policy=None, policy_cp=10, conversion=False, reductions=False, model=None, blend=0.0):
        self.policy, self.policy_cp = policy, policy_cp
        self.conversion, self.reductions, self.blend = conversion, reductions, float(blend)
        self.weights = np.zeros((768, 32), dtype=np.float32)
        self.bias = np.zeros(32, dtype=np.float32)
        self.output = np.zeros(32, dtype=np.float32)
        self.rule_weights = np.zeros((13, 32), dtype=np.float32)
        if model:
            with np.load(model, allow_pickle=False) as data:
                self.weights = data['weights'].astype(np.float32)
                self.bias = data['bias'].astype(np.float32)
                self.output = data['output'].astype(np.float32)
                self.rule_weights = data['rule_weights'].astype(np.float32)
            assert self.weights.shape == (768, 64) and self.bias.shape == self.output.shape == (64,)
            assert self.rule_weights.shape == (13, 64)
            assert all(np.isfinite(v).all() for v in (self.weights, self.bias, self.output, self.rule_weights))
        self.ttkey = np.zeros(1 << 18, dtype=np.uint64)
        self.ttcontext = np.zeros(1 << 18, dtype=np.uint64)
        self.ttdata = np.zeros((1 << 18, 5), dtype=np.int64)
        self.killers = np.zeros((100, 2), dtype=np.int64)
        self.history = np.zeros((2, 128, 128), dtype=np.int64)
        self.nodes = 0
        self.last_result = None

    def run(self, board, seconds=0.1, soft=None, max_depth=64, max_nodes=2**60,
            preferred_move=None, preference_cp=15):
        started = time.perf_counter()
        pieces, state = arrays(board)
        effective_blend = self.blend if board.fullmove_number > 12 else 0.0
        root = core.legal_moves(pieces, state)
        if len(root) == 0:
            return Result(None)
        hashes = np.zeros(800, dtype=np.uint64)
        replay = board.copy(stack=True)
        past = []
        for _ in range(min(board.halfmove_clock, len(board.move_stack)) + 1):
            b, s = arrays(replay)
            past.append(core.position_hash(b, s))
            if not replay.move_stack:
                break
            replay.pop()
        past.reverse()
        hashes[:len(past)] = past
        bonuses = np.zeros(len(root), dtype=np.int64)
        if seconds >= 0.05 and abs(core.classical(pieces, state)) < 300 and not board.is_check():
            # Same bounded policy preference as v1.14, with the same phase gate.
            phase = sum(int(core.PHASE[p.piece_type]) for p in board.piece_map().values())
            if phase > 4.8:
                decoded = [decode(int(m)) for m in root]
                values = self.policy.bonuses(board, decoded, self.policy_cp) if self.policy else {}
                for i, move in enumerate(decoded):
                    bonuses[i] = values.get(move, 0) + (preference_cp if move == preferred_move else 0)
        result = Result(decode(int(root[0])))
        control = np.array([0, 0, max_nodes], dtype=np.int64)
        deadline = started + max(0.0, seconds)
        soft_deadline = started + max(0.0, seconds if soft is None else soft)
        previous = int(root[0])
        for depth in range(1, max_depth + 1):
            if time.perf_counter() >= soft_deadline:
                break
            move, score, completed = core.root_iteration(
                pieces, state, depth, previous, root, bonuses, hashes, len(past), self.ttkey,
                self.ttcontext, self.ttdata, self.killers, self.history, control, deadline,
                self.weights, self.bias, self.output, self.rule_weights, effective_blend, self.conversion, self.reductions)
            if not completed:
                break
            previous = int(move)
            result = Result(decode(previous), int(score), depth)
            if abs(score) > 29900:
                break
        result.nodes, result.elapsed = int(control[0]), time.perf_counter() - started
        self.nodes, self.last_result = result.nodes, result
        return result

    def warmup(self):
        # Compile every runtime path before the match clock starts. No persistent cache.
        board = chess.Board()
        # Setup/JIT can consume the provisional deadline before run reaches
        # root_iteration. Always compile that path before emitting ready; the
        # external90s initialization watchdog remains the real startup limit.
        self.run(board, seconds=float('inf'), soft=float('inf'), max_depth=1, max_nodes=4096)
        self.ttkey.fill(0)
        self.ttcontext.fill(0)
        self.ttdata.fill(0)
        self.history.fill(0)
        self.killers.fill(0)
