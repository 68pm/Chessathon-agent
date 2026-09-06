import time
from collections import Counter

import chess
import numpy as np
import pytest

from engine.player_policy import SIZE, PlayerPolicy, encode_moves
from engine.search import Search, position_key
from engine.transposition import MATE
from nn.model import Network
from training.player_policy import choice_loss


def test_policy_features_mirror_and_inference_parity(tmp_path):
    board = chess.Board()
    for uci in ["e2e4", "c7c5", "g1f3", "b8c6"]:
        board.push_uci(uci)
    moves = list(board.legal_moves)
    mirrored = [
        chess.Move(
            chess.square_mirror(m.from_square), chess.square_mirror(m.to_square), m.promotion
        )
        for m in moves
    ]
    x = encode_moves(board, moves)
    assert np.array_equal(x, encode_moves(board.mirror(), mirrored))
    net = Network(inputs=SIZE, hidden=(64, 32))
    path = tmp_path / "policy.npz"
    net.save(path)
    policy = PlayerPolicy(path)
    assert np.max(np.abs(net.forward(x)[:, 0] - policy.logits(board, moves))) < 1e-6
    assert all(0 <= v <= 20 for v in policy.bonuses(board, moves).values())


def test_masked_choice_gradient():
    logits = np.array([[0.2, -0.4, 0.8], [-0.2, 1.1, 900.0]], dtype=np.float64)
    mask = np.array([[True, True, True], [True, True, False]])
    loss, gradient = choice_loss(logits, mask)
    assert np.isfinite(loss) and gradient[1, 2] == 0
    for index in np.ndindex(logits.shape):
        plus, minus = logits.copy(), logits.copy()
        plus[index] += 1e-5
        minus[index] -= 1e-5
        numerical = (choice_loss(plus, mask)[0] - choice_loss(minus, mask)[0]) / 2e-5
        assert abs(numerical - gradient[index]) < 1e-6


@pytest.mark.parametrize("depth", [1, 2])
def test_biased_alpha_beta_matches_full_window_and_restores_board(depth):
    class FixedPolicy:
        def bonuses(self, board, moves, max_cp):
            return {move: (move.to_square * 7) % (max_cp + 1) for move in moves}

    board, policy = chess.Board(), FixedPolicy()
    moves = list(board.legal_moves)
    bonuses = policy.bonuses(board, moves, 20)
    preferred = chess.Move.from_uci("e2e4")
    bonuses[preferred] = bonuses.get(preferred, 0) + 15
    reference = Search()
    reference.deadline, reference.nodes = time.perf_counter() + 5, 0
    reference.counts = Counter({position_key(board): 1})
    scores = {
        m: -reference.child(board, m, reference.negamax, depth - 1, -MATE - 1, MATE + 1, 1)
        + bonuses[m]
        for m in moves
    }
    result = Search(player_policy=policy).run(
        board, 3, max_depth=depth, preferred_move=preferred, preference_cp=15
    )
    assert result.depth == depth and scores[result.move] == max(scores.values())
    assert result.score == max(scores.values())
    assert board.fen() == chess.STARTING_FEN and not board.move_stack


def test_active_policy_cannot_override_proven_mate():
    class WrongPreference:
        called = False

        def bonuses(self, board, moves, max_cp):
            self.called = True
            return {move: 0 if move.uci() == "d8h4" else max_cp for move in moves}

    board, policy = chess.Board(), WrongPreference()
    for uci in ["f2f3", "e7e5", "g2g4"]:
        board.push_uci(uci)
    result = Search(player_policy=policy).run(
        board, 1, preferred_move=chess.Move.from_uci("a7a6"), preference_cp=25
    )
    board.push(result.move)
    assert policy.called and board.is_checkmate() and result.score == MATE - 1


def test_policy_is_bypassed_under_tiny_clock_or_in_check():
    class ForbiddenPolicy:
        def bonuses(self, *_args):
            raise AssertionError("Policy should be bypassed")

    for board, seconds in [
        (chess.Board(), 0.01),
        (chess.Board("4k3/8/8/8/8/8/4r3/4K3 w - - 0 1"), 0.1),
    ]:
        assert Search(player_policy=ForbiddenPolicy()).run(board, seconds).move in board.legal_moves
