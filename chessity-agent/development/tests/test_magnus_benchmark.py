from collections import Counter

from scripts.curriculum_benchmark import make_schedule
from scripts.magnus_benchmark import schedule, summary


def test_curriculum_schedule_has_equal_colour_pairs_and_fixed_opponents():
    jobs = make_schedule([[], [], [], [], [], ["e2e4", "c7c6", "d2d4", "d7d5"]])
    assert len(jobs) == 32
    counts = Counter((j["family"], j["elo"], j["white"]) for j in jobs)
    assert counts == Counter(
        {
            (family, elo, white): count
            for family, elo, count in [
                ("control", None, 4),
                ("baseline", None, 4),
                ("madchess", 1500, 2),
                ("madchess", 1700, 2),
                ("madchess", 1900, 2),
                ("stockfish", 1700, 2),
            ]
            for white in [True, False]
        }
    )


def test_fixed_ladder_balances_colours_and_includes_every_level():
    jobs = schedule([[], [], [], [], [], ["e2e4", "c7c6", "d2d4", "d7d5"]])
    assert len(jobs) == 92 and len({j["id"] for j in jobs}) == 92
    mad = [j for j in jobs if j["family"] == "madchess"]
    counts = Counter((j["elo"], j["white"]) for j in mad)
    assert counts == Counter(
        {(elo, white): 2 for elo in range(900, 2501, 100) for white in [True, False]}
    )


def test_highest_win_does_not_count_flags_draws_or_failures():
    rows = [
        dict(family="madchess", elo=elo, score=score, termination=term)
        for elo, score, term in [
            (1500, 1, "checkmate"),
            (1600, 0.5, "threefold_repetition"),
            (1700, 1, "flag"),
            (1800, None, "invalid"),
        ]
    ]
    result = summary(rows)
    assert result["highest_checkmate_win_by_family"]["madchess"] == 1500
