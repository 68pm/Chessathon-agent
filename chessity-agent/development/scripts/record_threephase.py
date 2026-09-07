"""Audit every completed phase match and select the upload by the frozen rule."""

import json
import shutil
import subprocess
import sys
import zipfile
from collections import Counter

from scripts.alien_rating_ladder import save_json, sha256
from scripts.fastchess_matches import score_summary
from scripts.magnus_benchmark import manifest
from scripts.record_fastchess import audit_game
from scripts.threephase_matches import CONFIG, RUN
from training.fastchess_data import ROOT


def read(path):
    return json.loads(path.read_text())


def audit_report(report):
    assert report["status"] == "complete"
    assert len(report["games"]) == len(report["schedule"])
    schedule = {row["id"]: row for row in report["schedule"]}
    assert len({row["id"] for row in report["games"]}) == len(schedule)
    for row in report["games"]:
        assert all(row[key] == value for key, value in schedule[row["id"]].items())
        audit_game(row, report["config"])
    if report.get("stage"):
        assert report["files"] == {name: manifest(ROOT / name) for name in report["files"]}
    else:
        assert report["files"] == manifest(ROOT / report["candidate"])
    for name, fingerprint in report["source_files"].items():
        assert sha256(ROOT / name) == fingerprint


def main():
    assert read(RUN / "final-cycle.json")["status"] == "complete"
    config = read(CONFIG)
    selection = read(RUN / "validation-selection.json")
    challenger = selection["challenger"]
    name = challenger.split("/")[-1]
    reports = {"baseline": read(RUN / "baseline/results.json"),
               "confirmation": read(RUN / f"confirmation-{name}/results.json"),
               "rated": read(RUN / f"rated-{name}/results.json")}
    for row in selection["candidates"]:
        candidate_name = row["candidate"].split("/")[-1]
        reports[f"development-{candidate_name}"] = read(RUN / f"development-{candidate_name}/results.json")
    endgames = {path: read(RUN / "endgames" / path.split("/")[-1] / "results.json")
                for path in dict.fromkeys([config["baseline"], challenger])}
    for report in [*reports.values(), *endgames.values()]:
        audit_report(report)
    evaluation = {path: read(RUN / "evaluation/test" / path.split("/")[-1] / "results.json")
                  for path in dict.fromkeys([config["baseline"], challenger])}
    for path, report in evaluation.items():
        assert report["status"] == "complete" and report["files"] == manifest(ROOT / path)
    confirmation = score_summary(reports["confirmation"]["games"])
    reasons = []
    if challenger == config["baseline"]:
        reasons.append("No eligible new implementation was selected.")
    if confirmation[config["baseline"]]["pair_bootstrap_95"][0] <= .5:
        reasons.append("Fresh paired 95% lower score bound versus v1.14 did not exceed 50%.")
    if confirmation[config["previous_newest"]]["score"] < .5:
        reasons.append("Fresh score versus v1.23 was below 50%.")
    candidate_games = reports["confirmation"]["games"] + reports["rated"]["games"] + endgames[challenger]["games"]
    if any(r.get("failed_colour") == ("white" if r["candidate_white"] else "black") for r in candidate_games):
        reasons.append("Candidate runtime failure occurred.")
    if any(r["illegal"] or r["clock_overruns"] for r in evaluation[challenger]["summary"].values()):
        reasons.append("Candidate failed legality or remaining-clock checks in held-out position tests.")
    selected = challenger if not reasons else config["baseline"]
    version = "v1.24" if selected == "candidates/threephase-pvs-v1" else "v1.14"
    archive = (ROOT / selected).with_suffix(".zip")
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        assert all(zipped.read(name) == (ROOT / selected / name).read_bytes() for name in zipped.namelist())
    check_path = RUN / "validate-selected-real-clock.json"
    subprocess.run([sys.executable, "-m", "scripts.validate_package", "--zip", str(archive),
                    "--clock-ms", "120000", "--calls", "2", "--out", str(check_path)], cwd=ROOT, check=True)
    check = read(check_path)
    assert all(value == "blocked" for value in check["read_only_checks"].values())
    stats = {label: score_summary(report["games"]) for label, report in reports.items()}
    result = dict(status="complete", selected_path=selected, public_version=version,
                  selected_zip_sha256=sha256(archive), candidate_promoted=not reasons, promotion_reasons=reasons,
                  challenger=challenger, time_control="120+0.5", matches=stats,
                  endgames={path: report["summary"] for path, report in endgames.items()},
                  test_positions={path: report["summary"] for path, report in evaluation.items()},
                  highest_candidate_winning_setting=max((r["elo"] for r in reports["rated"]["games"] if r["score"] == 1), default=None),
                  highest_baseline_winning_setting=max((r["elo"] for r in reports["baseline"]["games"] if r["score"] == 1), default=None),
                  audited_games=sum(len(r["games"]) for r in [*reports.values(), *endgames.values()]),
                  weights_updated=False, read_only_validation=check,
                  limitation="Nominal local Stockfish settings, not a calibrated human/site rating; endgame advantage drills excluded from highest rated win.")
    save_json(RUN / "selection.json", result)
    shutil.copy2(archive, ROOT.parent / "chessity-agent.zip")
    shutil.copy2((ROOT / challenger).with_suffix(".zip"), ROOT.parent / "chessity-agent-v1.24.zip")
    save_json(ROOT.parent / "chessity-agent-version.json", dict(name="chessity-agent", version=version,
              source_candidate=selected.split("/")[-1], sha256=sha256(archive), time_control="120+0.5",
              results=stats["rated"] if not reasons else stats["baseline"], read_only_checks=check["read_only_checks"]))
    evidence = ROOT / "docs/evidence"
    save_json(evidence / "threephase-selection.json", result)
    for label, report in reports.items():
        save_json(evidence / f"threephase-{label}.json", report)
        (evidence / f"threephase-{label}.pgn").write_text("\n\n".join(r["pgn"] for r in report["games"]) + "\n", encoding="utf-8")
    for path, report in endgames.items():
        save_json(evidence / f"threephase-endgames-{path.split('/')[-1]}.json", report)
    lines = ["# Three-phase pilot results", "", f"**Recommended upload: chessity-agent {version}.**", "",
             "The candidate keeps the existing locally trained policy and classical evaluation. It changes principal-variation search and quiescence move generation. No neural weights were fitted in this search experiment.", "",
             f"All {result['audited_games']} games passed legal PGN, clock, increment, schedule and frozen-source audits. Time control: 120 seconds plus 0.5 seconds per move; two simultaneous local games, one thread per engine. The local host is shared with other applications.", "",
             "## Fixed matches", "", "| Build / stage | Opponent | W | D | L | Score | Pair bootstrap 95% |", "|---|---|---:|---:|---:|---:|---|"]
    for stage, groups in stats.items():
        for opponent, group in groups.items():
            lines.append(f"| {stage} | {opponent} | {group['wins']} | {group['draws']} | {group['losses']} | {group['score']:.1%} | {group['pair_bootstrap_95']} |")
    lines += ["", f"Highest balanced-start winning setting: baseline {result['highest_baseline_winning_setting']}; candidate {result['highest_candidate_winning_setting']}. A single victory is not a stable rating. Small-sample intervals describe these opening pairs and do not cover opponent calibration or hardware differences.", "",
              "Promotion: " + ("passed the frozen rule." if not reasons else " ".join(reasons)), "",
              "## Held-out phase decisions", "", "| Build / mode | Accepted | 200cp blunders | Mean regret cp | Median ms |", "|---|---:|---:|---:|---:|"]
    for path, report in evaluation.items():
        for mode, group in report["summary"].items():
            lines.append(f"| {path.split('/')[-1]} / {mode} | {group['accepted']}/{group['positions']} | {group['blunders']} | {group['mean_regret_cp']} | {group['median_seconds']*1000:.1f} |")
    lines += ["", "The 96 test positions have 24 per phase. Modes reuse the same positions. Teacher estimates were verified at 80k/320k nodes, but remain finite-search estimates. The 192 diagnostic training positions did not fit weights. New whole-game/event/prefix grouping and exact/mirrored board exclusions reduce leakage; incomplete older source identities and semantic similarities remain limitations.", "",
              "## Endgame drills", "", "Advantageous KQK/KRK starts measure conversion; their wins do not count as defeating 2600 in ordinary games. Near-zero held-out endgames use finite teacher estimates and fresh repetition history at the recorded FEN, not tablebase certificates.", ""]
    for path, report in endgames.items():
        lines += [f"- {path.split('/')[-1]}: `{json.dumps(report['summary'])}`"]
    lines += ["", f"Terminations: `{json.dumps(dict(Counter(row['termination'] for report in reports.values() for row in report['games'])))}`.", "",
              "The public source ledger records supplied-source provenance separately from material inspected in this session. Raw historical scores, commercial texts and external engines are not runtime assets. All benchmark weights stayed fixed; game rewards were not used in this experiment. The separately requested elite-case learning experiment follows this frozen assessment.", ""]
    (ROOT / "docs/THREEPHASE_RESULTS.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({key: result[key] for key in ["public_version", "candidate_promoted", "promotion_reasons", "audited_games", "highest_candidate_winning_setting"]}, indent=2))


if __name__ == "__main__":
    main()
