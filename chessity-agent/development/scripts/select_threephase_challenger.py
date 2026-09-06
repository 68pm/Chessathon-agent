"""Apply the declared validation-only ranking before opening final test results."""

import argparse
import json

from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import manifest
from scripts.threephase_matches import CONFIG, RUN
from training.fastchess_data import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", action="append", required=True)
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text())
    out = RUN / "validation-selection.json"
    if out.exists():
        raise ValueError("Preserve the already frozen challenger selection")
    assert len(set(args.candidate)) == len(args.candidate) <= config["maximum_implementation_candidates"]
    rows = []
    for candidate in args.candidate:
        path = ROOT / candidate
        evaluation_path = RUN / "evaluation/validation" / path.name / "results.json"
        games_path = RUN / f"development-{path.name}/results.json"
        evaluation = json.loads(evaluation_path.read_text())
        games = json.loads(games_path.read_text())
        assert evaluation["status"] == games["status"] == "complete"
        assert evaluation["files"] == games["files"][candidate] == manifest(path)
        assert len(games["games"]) == config["development_pairs_per_candidate"] * 2
        timed = [evaluation["summary"][f"{mode}:all"] for mode in ["clock4000", "clock800"]]
        reliable = not any(r["illegal"] or r["clock_overruns"] for r in evaluation["summary"].values())
        reliable &= not any(r.get("failed_colour") == ("white" if r["candidate_white"] else "black") for r in games["games"])
        points = sum(r["score"] for r in games["games"])
        rank = [points, sum(r["accepted"] for r in timed), -sum(r["blunders"] for r in timed),
                evaluation["summary"]["nodes2000:all"]["accepted"], int(path.name == "threephase-pvs-v1")]
        rows.append(dict(candidate=candidate, eligible=bool(reliable), rank=rank,
                         validation_sha256=sha256(evaluation_path), development_sha256=sha256(games_path),
                         frozen_files=manifest(path)))
    eligible = [r for r in rows if r["eligible"]]
    challenger = max(eligible, key=lambda r: r["rank"])["candidate"] if eligible else config["baseline"]
    report = dict(status="frozen_before_final_tests", challenger=challenger, candidates=rows,
                  config_sha256=sha256(CONFIG), selection_source_sha256=sha256(__file__),
                  rule="Rank eligible implementations by development points, timed validation accepted choices, fewer timed blunders, equal-node accepted choices; exact ties prefer PVS. This does not promote the agent.",
                  no_eligible_implementation=not eligible)
    save_json(out, report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
