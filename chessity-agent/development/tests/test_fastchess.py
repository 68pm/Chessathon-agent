import chess
import chess.engine

from engine.search import Search
from engine.time_manager import allocate
from harness import referee
from training.fastchess_data import balanced, clear_observation, clock_regime, restore


class FakeAgent:
    def __init__(self, timer, seconds):
        self.timer, self.seconds, self.inputs = timer, seconds, []

    def start(self, _):
        pass

    def stop(self):
        pass

    def move(self, fen, remaining):
        self.inputs.append(remaining)
        self.timer[0] += self.seconds
        return next(iter(chess.Board(fen).legal_moves)).uci()


def test_actual_referee_adds_half_second_only_after_legal_on_time_move(monkeypatch):
    timer = [0.0]
    monkeypatch.setattr(referee.time, "monotonic", lambda: timer[0])
    white, black = FakeAgent(timer, 0.125), FakeAgent(timer, 0.125)
    outcome = referee.play_match(white, black, 120000, 500, ply_cap=3)
    assert outcome.termination == "ply_cap"
    assert white.inputs == [120000, 120375]
    assert black.inputs == [120000]


def test_increment_cannot_rescue_expired_submission(monkeypatch):
    timer = [0.0]
    monkeypatch.setattr(referee.time, "monotonic", lambda: timer[0])
    white, black = FakeAgent(timer, 120.001), FakeAgent(timer, 0)
    outcome = referee.play_match(white, black, 120000, 500)
    assert outcome.termination == "flag" and outcome.result == "black"
    assert not black.inputs


def test_actual_uci_transport_sends_fractional_increment(tmp_path):
    import sys

    script, commands = tmp_path / "uci_probe.py", tmp_path / "commands.txt"
    script.write_text(
        "import sys\nfrom pathlib import Path\n"
        "for line in sys.stdin:\n"
        "    line=line.strip()\n"
        "    if line == 'uci': print('id name TimingProbe\\nuciok', flush=True)\n"
        "    elif line == 'isready': print('readyok', flush=True)\n"
        "    elif line.startswith('go '):\n"
        "        Path(sys.argv[1]).write_text(line)\n"
        "        print('bestmove e2e4', flush=True)\n"
        "    elif line == 'quit': break\n", encoding="utf-8")
    with chess.engine.SimpleEngine.popen_uci([sys.executable, str(script), str(commands)]) as engine:
        result = engine.play(chess.Board(), chess.engine.Limit(white_clock=119.125, black_clock=120,
                                                              white_inc=0.5, black_inc=0.5))
        assert result.move == chess.Move.from_uci("e2e4")
    words = commands.read_text().split()
    assert words[words.index("winc") + 1] == words[words.index("binc") + 1] == "500"
    assert words[words.index("wtime") + 1] == "119125"


def test_equal_node_stop_preserves_board_and_available_move():
    board = chess.Board()
    original = board.fen()
    result = Search().run(board, seconds=30, max_nodes=150, adaptive_stop=True)
    assert result.nodes == 150 and result.move in board.legal_moves
    assert board.fen() == original and not board.move_stack


def test_adaptive_budget_reserves_clock_at_low_and_ordinary_times():
    for clock in [0, 20, 50, 500, 800, 2500, 10000, 120000]:
        quiet = allocate(clock, 25, 30, adaptive=True)
        checked = allocate(clock, 25, 30, adaptive=True, in_check=True)
        assert 0 <= quiet.soft <= quiet.hard <= clock / 1000
        assert 0 <= checked.soft <= checked.hard <= clock / 1000
        assert checked.soft >= quiet.soft
        if clock >= 50:
            assert checked.hard <= clock / 1000 - 0.029


def test_balancing_caps_games_and_history_is_verified():
    rows = [dict(id=str(i), player="p", solver_colour="white", primary_phase="opening",
                 clock_regime="ordinary", player_result="win", opening_family="italian",
                 family_id=str(i // 10)) for i in range(30)]
    selected = balanced(rows, 20, 7, per_game=2)
    assert len(selected) == 6
    assert clock_regime(2.99) == "under_3s" and clock_regime(3) == "under_10s"
    board = chess.Board()
    board.push_uci("e2e4")
    row = dict(solver_fen=board.fen(), relevant_history={"start_fen": chess.STARTING_FEN, "moves": ["e2e4"]})
    assert restore(row).move_stack == [chess.Move.from_uci("e2e4")]


def test_generated_positions_do_not_inherit_parent_human_clock_or_action():
    board = chess.Board()
    board.push_uci("e2e4")
    row = dict(solver_fen=board.fen(), fen=chess.STARTING_FEN, played_move_uci="e2e4",
               clock_after_recorded_seconds=179.0, clock_before_estimate_seconds=180.0,
               human_move_accepted=True, played_uci="e2e4")
    clear_observation(row)
    assert row["fen"] == board.fen() and row["played_uci"] is None and row["ply"] == 2
    assert "clock_after_recorded_seconds" not in row and "human_move_accepted" not in row


def test_promotion_needs_paired_evidence_and_reliability():
    from scripts.record_fastchess import promotion

    games = [dict(family=family, pair=pair, score=1.0, termination="checkmate", candidate_white=white,
                  failed_colour=None) for family in ["previous_best", "matched_control", "static_clock"]
             for pair in range(2) for white in [True, False]]
    assert promotion({"games": games}, {"games": []}, {"rows": []})[0]
    for row in games:
        if row["family"] == "previous_best":
            row["score"] = 0.5
    assert not promotion({"games": games}, {"games": []}, {"rows": []})[0]
    for row in games:
        row["score"] = 1.0
    games[0]["termination"] = "flag"
    assert not promotion({"games": games}, {"games": []}, {"rows": []})[0]


def test_new_match_loop_checks_expiration_before_parsing_a_late_move(monkeypatch, tmp_path):
    from scripts import fastchess_matches

    timer = [0.0]

    class LateMalformed(FakeAgent):
        def move(self, fen, remaining):
            super().move(fen, remaining)
            return "not-a-move"

    white, black = LateMalformed(timer, 120.001), FakeAgent(timer, 0)
    agents = iter([white, black])
    monkeypatch.setattr(fastchess_matches, "local", lambda _: next(agents))
    monkeypatch.setattr(fastchess_matches.time, "perf_counter", lambda: timer[0])
    job = dict(id=1, family="test", pair=0, candidate_white=True, opening=[], opponent_path="test-placeholder")
    row = fastchess_matches.run_game(job, dict(base_ms=120000, increment_ms=500, ply_cap=600), tmp_path)
    assert row["termination"] == "flag" and row["score"] == 0
    assert row["failed_colour"] == "white" and not black.inputs
