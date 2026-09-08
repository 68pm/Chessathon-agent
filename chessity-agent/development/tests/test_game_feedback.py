import io

import chess
import chess.pgn
import numpy as np
import pytest

from training.game_feedback import grade, normalise_game
from training.reward_policy import probabilities, reward_loss


def value(cp=0, move='e2e4', mate=None):
    return dict(cp=None if mate is not None else cp, mate=mate, pv=[move])


def pair(best, played):
    return [dict(best=best, played=played), dict(best=best.copy(), played=played.copy())]


def test_reward_does_not_depend_on_result_or_colour():
    good = grade(pair(value(180), value(170)), 'e2e4', 20)
    assert good['reward'] == 1 and good['policy_target'] == 'e2e4'
    bad = grade(pair(value(-100, 'e2e4'), value(-450, 'd2d4')), 'd2d4', 20)
    assert bad['reward'] == -1 and bad['label'] == 'major_mistake'
    assert bad['policy_target'] == 'e2e4'
    assert grade(pair(value(900), value(890)), 'e2e4', 1)['reward'] == 0


def test_unstable_and_contradictory_teacher_values_do_not_train():
    unstable = pair(value(150), value(150))
    unstable[1]['played'] = value(-100)
    result = grade(unstable, 'e2e4', 20)
    assert result['reward'] is None and result['policy_target'] is None
    reverse = grade(pair(value(20), value(100)), 'e2e4', 20)
    assert reverse['reward'] is None
    different_best = pair(value(200), value(-150, 'd2d4'))
    different_best[1]['best'] = value(200, 'g1f3')
    result = grade(different_best, 'd2d4', 20)
    assert result['reward'] == -1 and result['policy_target'] is None


def test_mate_is_categorical_and_already_lost_positions_are_not_repunished():
    assert grade(pair(value(mate=3), value(mate=5)), 'e2e4', 20)['reward'] == 1
    assert grade(pair(value(mate=-5), value(mate=-2)), 'e2e4', 20)['reward'] == 0
    assert grade(pair(value(0), value(mate=-3)), 'e2e4', 20)['reward'] == -1
    assert grade(pair(value(mate=3), value(100)), 'e2e4', 20)['reward'] == -1
    assert grade(pair(value(mate=3), value(100)), 'e2e4', 20)['regret_cp'] is None


def test_reward_gradient_reinforces_good_and_reduces_bad_action_probability():
    logits = np.array([0., 0., 0.], dtype=np.float64)
    anchor = probabilities(logits)
    _, gradient = reward_loss(logits, 0, 1., anchor)
    after = probabilities(logits - .1 * gradient)
    assert after[0] > anchor[0] and after[1] < anchor[1]
    # Finite differences verify the actual objective/gradient, including the anchor.
    point = np.array([.3, -.4, .2])
    _, analytic = reward_loss(point, 2, .6, anchor)
    for i in range(3):
        epsilon = np.zeros(3)
        epsilon[i] = 1e-5
        high = reward_loss(point + epsilon, 2, .6, anchor)[0]
        low = reward_loss(point - epsilon, 2, .6, anchor)[0]
        assert analytic[i] == pytest.approx((high - low) / 2e-5, abs=1e-7)


def test_pgn_history_survives_and_mixed_version_games_stay_separate():
    pgn = '[White "Chessity"]\n[Black "Control"]\n[Result "1/2-1/2"]\n\n1. Nf3 Nf6 2. Ng1 Ng8 3. Nf3 Nf6 4. Ng1 Ng8 1/2-1/2'
    row = dict(pgn=pgn, candidate_white=True, candidate_version='v1.41')
    game, info = normalise_game(row)
    board = game.end().board()
    assert board.is_repetition(3)
    assert len(info['moves']) == 8
    _, later = normalise_game(dict(row, candidate_version='v1.53'))
    assert later['game_key'] != info['game_key']
    with pytest.raises(ValueError, match='score disagree'):
        normalise_game(dict(row, score=1))


def test_nonstandard_start_does_not_replay_opening_twice():
    board = chess.Board()
    board.push_san('e4')
    game = chess.pgn.Game.from_board(chess.Board(board.fen()))
    game.add_main_variation(chess.Move.from_uci('e7e5'))
    game.headers['Result'] = '1/2-1/2'
    row = dict(pgn=str(game), candidate_white=False)
    parsed, info = normalise_game(row)
    assert parsed.board().fen() == board.fen() and info['moves'] == ['e7e5']
    assert chess.pgn.read_game(io.StringIO(str(parsed))).end().board().is_valid()
