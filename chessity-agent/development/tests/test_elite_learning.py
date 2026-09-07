import copy

import chess
import chess.engine
import pytest

from training.elite_cases import completed_iteration, extract_cases
from training.elite_train import outcome_target


def update(depth, rank, uci, cp, **extra):
    return dict(depth=depth, multipv=rank, pv=[chess.Move.from_uci(uci)],
                score=chess.engine.PovScore(chess.engine.Cp(cp), chess.WHITE), nodes=depth * 1000, **extra)


def test_teacher_uses_complete_common_depth_and_discards_bounds():
    data = [update(2, 1, "e2e4", 20), update(2, 2, "d2d4", 15),
            update(3, 1, "e2e4", 99, lowerbound=True), update(3, 2, "d2d4", 10),
            dict(depth=4, nodes=4000)]
    answer = completed_iteration(data, {"e2e4", "d2d4"}, chess.WHITE)
    assert {value["depth"] for value in answer.values()} == {2}
    assert answer["e2e4"]["cp"] == 20
    assert answer["e2e4"]["total_search_nodes_observed"] == 4000


def test_teacher_rejects_duplicate_roots_and_preserves_perspective():
    with pytest.raises(ValueError, match="common-depth"):
        completed_iteration([update(3, 1, "e2e4", 20), update(3, 2, "e2e4", 10)], {"e2e4", "d2d4"}, chess.WHITE)
    answer = completed_iteration([update(3, 1, "e2e4", 20)], {"e2e4"}, chess.BLACK)
    assert answer["e2e4"]["cp"] == -20


def test_outcome_reward_only_reinforces_verified_sound_choices():
    row = dict(target_distribution={"e2e4": .6, "d2d4": .3, "f2f3": .1},
               acceptable_first_moves=["e2e4", "d2d4"], played_uci="d2d4", training_game_score=1)
    original = copy.deepcopy(row)
    target, alpha = outcome_target(row)
    assert alpha == .1 and target["d2d4"] == pytest.approx(.37)
    assert sum(target.values()) == pytest.approx(1)
    assert row == original
    row["played_uci"] = "f2f3"
    target, alpha = outcome_target(row)
    assert target == row["target_distribution"] and alpha == 0
    row.update(played_uci="d2d4", training_game_score=0)
    assert outcome_target(row)[1] == 0
    row["training_game_score"] = .5
    assert outcome_target(row)[1] == .05
    row["training_game_score"] = 2
    with pytest.raises(ValueError):
        outcome_target(row)


def test_case_parser_deduplicates_and_checks_actual_legality():
    document = f"""## Case 1
**Position ID:** `123:player:1`
**Played:** `1.e4`.
```text
{chess.STARTING_FEN}
```
## 1. Duplicate format
Position `123:player:1`; context.
**Observed decision:** e4. Extra source information.
```text
{chess.STARTING_FEN}
```
"""
    rows, entries = extract_cases(document)
    assert entries == 2 and len(rows) == 1
    assert rows[0]["played_uci"] == "e2e4" and rows[0]["split"] == "train"
    assert not rows[0]["relevant_history"]["complete"]
    with pytest.raises(chess.IllegalMoveError):
        extract_cases(document.replace("1.e4", "1.e5"))
