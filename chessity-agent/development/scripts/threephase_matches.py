"""Resumable, frozen games for the three-phase pack; reuses the tested actual referee."""

import argparse
import concurrent.futures
import ctypes
import json
import logging
import os
from datetime import datetime, timezone

from scripts.alien_rating_ladder import save_json, sha256
from scripts.fastchess_matches import run_game, score_summary
from scripts.magnus_benchmark import SF, manifest
from training.fastchess_data import ROOT

CONFIG = ROOT / "configs/threephase-pilot.json"
RUN = ROOT / "runs/threephase-pilot-20260906"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["baseline", "development", "confirmation", "rated"], required=True)
    parser.add_argument("--candidate")
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text())
    assert (config["base_ms"], config["increment_ms"], config["ply_cap"]) == (120000, 500, 600)
    assert sha256((ROOT / config["baseline"]).with_suffix(".zip")) == config["baseline_zip_sha256"]
    candidate = args.candidate or config["baseline"]
    path = (ROOT / candidate).resolve()
    assert path.is_relative_to(ROOT.resolve()) and (path / "agent.py").is_file()
    candidate = path.relative_to(ROOT.resolve()).as_posix()
    openings = json.loads((ROOT / "configs/fastchess-openings.json").read_text())
    jobs = []
    if args.stage in {"baseline", "rated"}:
        if args.stage == "baseline":
            assert candidate == config["baseline"]
        count = config["baseline_pairs_per_setting"] if args.stage == "baseline" else config["final_pairs_per_setting"]
        for elo in config["rated_settings"]:
            for pair, opening in enumerate(openings[:count]):
                for white in [True, False]:
                    jobs.append(dict(family=f"stockfish:{elo}", elo=elo, pair=pair, opening=opening, candidate_white=white))
    else:
        opponents = [(config["baseline"], config["development_pairs_per_candidate"])] if args.stage == "development" else [
            (config["baseline"], config["confirmation_pairs"]), (config["previous_newest"], config["previous_newest_pairs"])]
        for opponent, count in opponents:
            for pair, opening in enumerate(openings[:count]):
                for white in [True, False]:
                    jobs.append(dict(family=opponent, opponent_path=opponent, pair=pair, opening=opening, candidate_white=white))
    jobs = [dict(id=i + 1, candidate_path=candidate, **job) for i, job in enumerate(jobs)]
    label = args.stage if args.stage == "baseline" else f"{args.stage}-{path.name}"
    out = RUN / label
    paths = {candidate, *[j["opponent_path"] for j in jobs if "opponent_path" in j]}
    frozen = {p: manifest(ROOT / p) for p in paths}
    sources = {p: sha256(ROOT / p) for p in ["scripts/threephase_matches.py", "scripts/fastchess_matches.py", "harness/sandbox.py"]}
    report_path = out / "results.json"
    if out.exists():
        if not args.resume:
            raise ValueError("Preserve existing games; use --resume after inspecting a stopped run")
        report = json.loads(report_path.read_text())
        assert report["config"] == config and report["schedule"] == jobs and report["files"] == frozen
        assert report["source_files"] == sources
        if report["status"] == "complete":
            print("This fixed match stage is already complete.")
            return
        report.setdefault("resumes", []).append(datetime.now(timezone.utc).isoformat())
        report.pop("error", None)
    else:
        out.mkdir(parents=True)
        report = dict(config=config, stage=args.stage, candidate=candidate, schedule=jobs, files=frozen,
                      source_files=sources, config_sha256=sha256(CONFIG), games=[], started_utc=datetime.now(timezone.utc).isoformat(),
                      stockfish_sha256=sha256(SF), logical_cpus=os.cpu_count(),
                      scope="Fixed nominal Stockfish settings; no human/site Elo claim. Two local games at a time; single-thread engines, no pondering or external teacher at agent inference.")
    assert report["stockfish_sha256"] == "45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0"
    completed = {row["id"]: row for row in report["games"]}
    # A completed game file survives a controller interruption before its aggregate save.
    for job in jobs:
        game_path = out / f"game-{job['id']:03}.json"
        if game_path.exists() and job["id"] not in completed:
            row = json.loads(game_path.read_text())
            assert all(row[k] == v for k, v in job.items())
            completed[job["id"]] = row
    report.update(status="running", games=sorted(completed.values(), key=lambda row: row["id"]))
    save_json(report_path, report)
    logging.getLogger("chess.engine").setLevel(logging.ERROR)
    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=config["workers"]) as pool:
            pending = [pool.submit(run_game, job, config, out) for job in jobs if job["id"] not in completed]
            for future in concurrent.futures.as_completed(pending):
                row = future.result()
                report["games"].append(row)
                report["games"].sort(key=lambda item: item["id"])
                report["summary"] = score_summary(report["games"])
                save_json(report_path, report)
                print(f"{label} {len(report['games'])}/{len(jobs)}: {row['family']} {row['score']} {row['termination']}", flush=True)
        assert frozen == {p: manifest(ROOT / p) for p in paths}
        report.update(status="complete", completed_utc=datetime.now(timezone.utc).isoformat())
    except BaseException as error:
        report.update(status="failed", error=repr(error))
        raise
    finally:
        save_json(report_path, report)
        if os.name == "nt":
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == "__main__":
    main()
