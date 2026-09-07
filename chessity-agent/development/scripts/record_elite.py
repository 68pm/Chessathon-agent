"""Audit the elite learning pilot, report actual rewards/results and preserve the strongest verified ZIP."""

import json
import math
import shutil
import subprocess
import sys
from collections import Counter

import chess
import numpy as np

from engine.player_policy import PlayerPolicy
from scripts.alien_rating_ladder import save_json, sha256
from scripts.fastchess_matches import score_summary
from scripts.magnus_benchmark import manifest
from scripts.puzzle_evaluate import judge
from scripts.record_fastchess import audit_game
from training.elite_cases import CONFIG, RUN
from training.fastchess_data import ROOT, read_rows


def read(path):
    return json.loads(path.read_text())


def wilson(wins, count):
    z, p = 1.959963984540054, wins / count
    centre = (p + z*z / (2*count)) / (1 + z*z/count)
    radius = z * math.sqrt(p*(1-p)/count + z*z/(4*count*count)) / (1 + z*z/count)
    return [max(0, centre-radius), min(1, centre+radius)]


def case_assessment(paths):
    cases = read_rows(RUN / "cases/verified.jsonl")
    result = {}
    for path in paths:
        policy = PlayerPolicy(ROOT / path / "models/player-policy.npz")
        rows = []
        for row in cases:
            board = chess.Board(row["solver_fen"])
            moves = list(board.legal_moves)
            chosen = moves[int(np.argmax(policy.logits(board, moves)))].uci()
            rows.append(dict(id=row["id"], move=chosen, assessment=judge(row, chosen)))
        result[path] = dict(positions=len(rows), accepted=sum(r["assessment"]["accepted"] for r in rows),
                           verified_blunders=sum(r["assessment"].get("blunder") is True for r in rows), rows=rows)
    return dict(scope="Raw-policy recognition on training cases; this is recall, not held-out strength or a production-search result.", models=result)


def main():
    session = read(RUN / "session.json")
    assert session["status"] == "complete"
    config, frozen = read(CONFIG), read(RUN / "validation-selection.json")
    challenger, control, baseline = [frozen[key] for key in ["challenger", "control", "baseline"]]
    assert frozen["files"] == {path: manifest(ROOT / path) for path in frozen["files"]}
    reports = {stage: read(RUN / stage / "results.json") for stage in ["adaptation", "confirmation", "rated"]}
    assert all(report["status"] == "complete" for report in reports.values())
    assert len(reports["adaptation"]["games"]) == config["training_rounds"] * 4
    for stage in ["confirmation", "rated"]:
        report = reports[stage]
        assert len(report["games"]) == len(report["schedule"])
        assert {row["id"] for row in report["games"]} == {row["id"] for row in report["schedule"]}
        schedule = {row["id"]: row for row in report["schedule"]}
        for row in report["games"]:
            assert all(row[key] == value for key, value in schedule[row["id"]].items())
        assert report["files"] == {path: manifest(ROOT / path) for path in report["files"]}
        assert all(sha256(ROOT / path) == fingerprint for path, fingerprint in report["source_files"].items())
    for report in reports.values():
        for game in report["games"]:
            audit_game(game, config)
    registry = read(RUN / "candidate-index.json")
    by_path = {row["candidate"]: row for row in registry}
    for path, row in by_path.items():
        assert sha256((ROOT / path).with_suffix(".zip")) == row["sha256"]
        assert sha256(ROOT / path / "models/player-policy.npz") == row["policy_sha256"]
    review_stats, all_verified = [], {}
    for game in reports["adaptation"]["games"]:
        folder = RUN / "reviews" / f"game-{game['id']:03}"
        review = read(folder / "review.json")
        assert review["status"] == "complete" and review["game_sha256"] == sha256(RUN / "adaptation" / f"game-{game['id']:03}.json")
        assert review["all_moves_attempted"] == len(game["moves"])
        verified = read_rows(folder / "verified.jsonl")
        assert sha256(folder / "verified.jsonl") == read(folder / "manifest.json")["verified_sha256"]
        for row in verified:
            if row["split"] == "train":
                assert row["training_game_score"] == game["score"]
                all_verified[row["id"]] = row
        review_stats.append({key: review[key] for key in ["game_id", "result", "all_moves_attempted", "all_moves_verified", "own_verified", "verified_own_blunders"]})
    training, reinforced, winning_reinforced = {}, set(), set()
    stages = ["seed"] + [f"after-game-{index:02}" for index in range(1, len(reports["adaptation"]["games"]) + 1)]
    for stage in stages:
        folder = RUN / "training" / stage
        report, order = read(folder / "report.json"), read(folder / "training-order.json")
        assert report["status"] == "complete" and order["validation_or_test_replay"] == 0
        assert all(max(ids) < order["training_count"] for ids in order["indices_by_epoch"])
        sampled = {order["ids"][index] for ids in order["indices_by_epoch"] for index in ids}
        for boost in order["reward_boosts"]:
            row = all_verified[boost["id"]]
            assert boost["id"] in sampled and row["played_uci"] in row["acceptable_first_moves"]
            assert boost["score"] == row["training_game_score"] and boost["alpha"] == .1 * boost["score"]
            reinforced.add(boost["id"])
            if boost["score"] == 1:
                winning_reinforced.add(boost["id"])
        training[stage] = {recipe: {key: values[key] for key in ["selected_epoch", "parameter_l2_change", "sha256", "seconds"]}
                           for recipe, values in report["recipes"].items()}
    comparison, rated = [score_summary(reports[stage]["games"]) for stage in ["confirmation", "rated"]]
    reasons = []
    baseline_parameters = PlayerPolicy(ROOT / baseline / "models/player-policy.npz").p
    challenger_parameters = PlayerPolicy(ROOT / challenger / "models/player-policy.npz").p
    if all(np.array_equal(before, after) for before, after in zip(baseline_parameters, challenger_parameters, strict=True)):
        reasons.append("Selected policy parameters are unchanged from the preserved best; timing noise cannot establish a model improvement.")
    if comparison[baseline]["pair_bootstrap_95"][0] <= .5:
        reasons.append("Fresh paired 95% lower score bound versus the preserved best did not exceed 50%.")
    if comparison[control]["score"] < .5:
        reasons.append("The outcome candidate scored below 50% versus the matched teacher-only ablation.")
    if any(row.get("failed_colour") == ("white" if row["candidate_white"] else "black")
           for stage in ["confirmation", "rated"] for row in reports[stage]["games"]):
        reasons.append("Candidate reliability failure occurred in fresh evaluation.")
    selected = baseline if reasons else challenger
    phase = read(ROOT / "runs/threephase-pilot-20260906/selection.json")
    version = phase["public_version"] if reasons else by_path[challenger]["public_version"]
    for stats in rated.values():
        stats["outright_win_rate_95_wilson"] = wilson(stats["wins"], stats["games"])
        stats["consistency_pilot_criterion_met"] = stats["outright_win_rate_95_wilson"][0] > .5
    case_results = case_assessment([baseline, challenger, control])
    save_json(RUN / "case-recognition.json", case_results)
    selected_zip = (ROOT / selected).with_suffix(".zip")
    check_path = RUN / "selected-read-only-check.json"
    subprocess.run([sys.executable, "-m", "scripts.validate_package", "--zip", str(selected_zip),
                    "--calls", "2", "--clock-ms", "120000", "--out", str(check_path)], cwd=ROOT, check=True)
    check = read(check_path)
    assert check["sha256"] == sha256(selected_zip) and all(value == "blocked" for value in check["read_only_checks"].values())
    result = dict(status="complete", selected_path=selected, public_version=version,
                  selected_zip_sha256=sha256(selected_zip), candidate_promoted=not reasons, promotion_reasons=reasons,
                  challenger=challenger, control=control, comparison=comparison, rated=rated,
                  highest_fresh_candidate_winning_setting=max((row["elo"] for row in reports["rated"]["games"] if row["score"] == 1), default=None),
                  adaptation_outcomes=dict(Counter(str(row["score"]) for row in reports["adaptation"]["games"])),
                  reviews=review_stats, training=training, unique_reinforced_sound_choices=len(reinforced),
                  unique_reinforced_winning_choices=len(winning_reinforced),
                  audited_games=sum(len(report["games"]) for report in reports.values()),
                  source_cases=read(RUN / "case-import.json"), verified_cases=read(RUN / "cases/manifest.json"),
                  read_only_validation=check, time_control="120+0.5",
                  limitation="Nominal local Stockfish handicap settings, not calibrated human/site Elo. Adaptive training games are excluded from strength claims; final weights were frozen.")
    save_json(RUN / "selection.json", result)
    shutil.copy2(selected_zip, ROOT.parent / "chessity-agent.zip")
    for row in registry:
        shutil.copy2((ROOT / row["candidate"]).with_suffix(".zip"), ROOT.parent / f"chessity-agent-{row['public_version']}.zip")
    save_json(ROOT.parent / "chessity-agent-version.json", dict(name="chessity-agent", version=version,
              source_candidate=selected.split("/")[-1], sha256=sha256(selected_zip), time_control="120+0.5",
              read_only_checks=check["read_only_checks"], new_candidate_results=rated,
              selected_evidence="docs/ELITE_LEARNING_RESULTS.md" if not reasons else "docs/THREEPHASE_RESULTS.md"))
    evidence = ROOT / "docs/evidence"
    for name, value in [("selection", result), ("case-recognition", case_results), *reports.items()]:
        save_json(evidence / f"elite-{name}.json", value)
        if "games" in value:
            (evidence / f"elite-{name}.pgn").write_text("\n\n".join(row["pgn"] for row in value["games"]) + "\n", encoding="utf-8")
    lines = ["# Elite-case outcome-guided learning pilot", "", f"**Recommended upload: chessity-agent {version}.**", "",
             "## Data and actual learning", "",
             f"The supplied Markdown provided 22 case entries: 21 distinct legal positions from 20 games. The referenced 1,862-game companion corpus was not present and was not used. Independent 80k/320k-node teacher verification accepted {result['verified_cases']['accepted']} cases and quarantined {result['verified_cases']['quarantined']}. Supplied cases lack full preceding game history, a limitation kept in their metadata.", "",
             "The existing 935–64–32–1 move-ranking network received the verified cases alongside train-only Carlsen/Witty, puzzle and three-phase replay. The classical evaluator, search, original clock controller and optional Alien preference were copied from the preserved best. Prose explanations were converted to board/move supervision; this network does not ingest or reason over the document's text.", "",
             "After every adaptation game, every recorded ply was submitted for independent Stockfish review. Stable candidate decisions, corrections and refutations entered the next weight update; unstable or non-exact mate-scored roots were quarantined. Opponent moves were reviewed as context and never treated as the candidate's rewarded choices. Lost games still supplied corrected targets.", "",
             f"The outcome branch mixed up to 10% extra probability into a verified sound move from a win (5% for a draw). It reinforced {len(reinforced)} distinct sampled sound choices, including {len(winning_reinforced)} from wins. This is outcome-guided supervised learning, not a policy-gradient reinforcement-learning algorithm. A terminal result never becomes a forced-win label for an earlier position. A matched teacher-only branch trained on the same examples and update schedule without the outcome bonus.", "",
             "Epoch zero remained eligible: a training update was retained only when it improved the fixed validation objective (50% broad, 30% phase, 20% puzzle cross-entropy). Whole known source games and exact/mirrored validation-board collisions were excluded from replay. Unknown older source identities and related positions remain possible. Training games changed checkpoints after each game and are excluded from strength estimates.", "",
             "| Training stage | Branch | Selected epoch | Parameter L2 change |", "|---|---|---:|---:|"]
    for stage, recipes in training.items():
        for recipe, item in recipes.items():
            lines.append(f"| {stage} | {recipe} | {item['selected_epoch']} | {item['parameter_l2_change']:.6f} |")
    lines += ["", "## Fresh frozen evaluation at 120+0.5", "", "| Opponent | W | D | L | Score | Paired 95% score interval |", "|---|---:|---:|---:|---:|---|"]
    for opponent, item in {**comparison, **rated}.items():
        lines.append(f"| {opponent} | {item['wins']} | {item['draws']} | {item['losses']} | {item['score']:.1%} | {item['pair_bootstrap_95']} |")
    lines += ["", f"Highest nominal setting defeated by the new candidate in fresh games: {result['highest_fresh_candidate_winning_setting']}. Promotion: " + ("passed the declared rule." if not reasons else " ".join(reasons)), "",
              "The practical consistency target requires the lower 95% Wilson bound on outright wins to exceed 50% at each setting. Wilson intervals assume independent game outcomes; the accompanying paired bootstrap reflects opening-pair clustering. This small fixed pilot cannot certify future win rates, hardware independence or a human/site rating.", ""]
    for opponent, item in rated.items():
        lines.append(f"- {opponent}: outright-win interval {item['outright_win_rate_95_wilson']}; pilot criterion {'met' if item['consistency_pilot_criterion_met'] else 'not met'}.")
    lines += ["", "## Training-case recognition", "", "| Build | Raw-policy accepted | Verified blunders |", "|---|---:|---:|"]
    for path, item in case_results["models"].items():
        lines.append(f"| {path} | {item['accepted']}/{item['positions']} | {item['verified_blunders']} |")
    lines += ["", "These are training-case recall measurements, not new held-out tactical strength or actual search choices.", "",
              "## Per-game review coverage", "", "| Training game | Score | All plies attempted | Verified plies | Verified own moves | Verified own blunders |", "|---|---:|---:|---:|---:|---:|"]
    for item in review_stats:
        lines.append(f"| {item['game_id']} | {item['result']} | {item['all_moves_attempted']} | {item['all_moves_verified']} | {item['own_verified']} | {item['verified_own_blunders']} |")
    lines += ["", f"All {result['audited_games']} game records passed schedule, legal-move, clock, increment and frozen-runtime audits. The selected ZIP passed read-only execution checks. Offline Stockfish executables and teacher labels are excluded from competition archives. The two-round budget ended as declared; no extra games were added to chase a high-rated win.", ""]
    (ROOT / "docs/ELITE_LEARNING_RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ["public_version", "candidate_promoted", "highest_fresh_candidate_winning_setting", "audited_games", "unique_reinforced_winning_choices"]}, indent=2))


if __name__ == "__main__":
    main()
