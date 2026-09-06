import chess
import pytest

from engine.fusion import RootFusion
from engine.search import Search


class Policy:
    def bonuses(self, board, moves, max_cp):
        return dict.fromkeys(moves, max_cp)


class Value:
    def centipawns(self, board):
        # A positive value after e4/e5 means the opponent is better, not the root player.
        return 100 if board.peek().uci() in {"e2e4", "e7e5"} else 0


def test_root_fusion_negates_child_perspective_for_both_colours_and_is_bounded():
    for board, bad, good in [(chess.Board(), "e2e4", "d2d4"),
                             (chess.Board().mirror(), "e7e5", "d7d5")]:
        fen = board.fen()
        policy = RootFusion(Policy(), Value())
        bonuses = policy.bonuses(board, list(board.legal_moves), 15)
        assert bonuses[chess.Move.from_uci(good)] > bonuses[chess.Move.from_uci(bad)]
        assert all(0 <= score <= 15 for score in bonuses.values())
        assert board.fen() == fen and not board.move_stack


def test_root_fusion_restores_board_if_model_fails():
    class Broken:
        def centipawns(self, board):
            raise RuntimeError("test failure")
    board = chess.Board()
    before = board.fen()
    with pytest.raises(RuntimeError, match="test failure"):
        RootFusion(Policy(), Broken()).bonuses(board, list(board.legal_moves), 15)
    assert board.fen() == before and not board.move_stack


def test_mate_and_draw_endpoints_never_use_an_approximate_value():
    class Guard:
        def centipawns(self, board):
            assert not board.is_game_over(claim_draw=True)
            return 0
    board = chess.Board("7k/8/5KQ1/8/8/8/8/8 w - - 0 1")
    fusion = RootFusion(Policy(), Guard())
    bonuses = fusion.bonuses(board, list(board.legal_moves), 15)
    assert bonuses[chess.Move.from_uci("g6g7")] == 15
    chosen = Search(player_policy=fusion, policy_cp=15).run(board, seconds=0.2, max_depth=2).move
    board.push(chosen)
    assert board.is_checkmate()
    drawn = chess.Board("8/k1P5/2K5/8/8/8/8/8 w - - 0 1")
    fusion.bonuses(drawn, list(drawn.legal_moves), 15)
    assert drawn.is_valid() and not drawn.move_stack


def test_final_schedule_balances_every_pair_and_uses_competition_clock():
    import json
    from pathlib import Path

    from scripts.final_fusion_benchmark import AGENTS, schedule
    config = json.loads(Path("configs/final-fusion.json").read_text())
    assert config["base_ms"] == 120000 and config["increment_ms"] == 500
    assert config["ply_cap"] == 600
    jobs = schedule(json.loads(Path("configs/mixed-benchmark-openings.json").read_text()))
    assert len(jobs) == 30
    for name in AGENTS:
        assert sum(r["white"] == name for r in jobs) == 5
        assert sum(r["black"] == name for r in jobs) == 5
    for row in jobs:
        reverse = [r for r in jobs if r["white"] == row["black"] and r["black"] == row["white"]]
        assert len(reverse) == 1 and reverse[0]["opening"] == row["opening"]
