from collections import Counter

import chess
import pytest

from training.chess_curriculum import PHASES, PLAYERS, choose, describe


def test_phase_uses_position_not_move_number():
    board = chess.Board()
    first = describe(board, chess.Move.from_uci("e2e4"))
    board.fullmove_number = 99
    assert describe(board, chess.Move.from_uci("e2e4")) == first
    assert first["primary_phase"] == "opening"


def test_king_activity_can_also_be_necessary_defence_in_an_ending():
    board = chess.Board("7k/8/8/8/8/8/7r/7K w - - 0 1")
    move = chess.Move.from_uci("h1h2")
    assert move in board.legal_moves
    result = describe(board, move)
    assert result["primary_phase"] == "endgame"
    assert "necessary_defence" in result["concept_tags"]
    assert "played_king_move" in result["concept_tags"]
    assert "reward" not in result


def test_phase_sampling_keeps_player_shares_unique_and_bounded():
    rows = [
        {
            "player": player,
            "primary_phase": phase,
            "fen": f"synthetic-{player}-{phase}-{i}",
            "played_uci": "e2e4",
        }
        for player in PLAYERS
        for phase in PHASES
        for i in range(10)
    ]
    for balanced in [True, False]:
        result = choose(rows, 40, balanced, 123)
        assert len(result) == len({r["fen"] for r in result}) == 40
        assert Counter(r["player"] for r in result) == Counter({p: 20 for p in PLAYERS})
    with pytest.raises(ValueError, match="Insufficient"):
        choose(rows, 1000, True, 123)
