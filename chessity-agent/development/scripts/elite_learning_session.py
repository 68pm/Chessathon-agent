"""Finish the frozen phase experiment, then run the bounded elite-case learning pilot."""

import argparse
import concurrent.futures
import ctypes
import json
import os

for variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
    os.environ[variable] = "1"

import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

import chess

from scripts.alien_rating_ladder import save_json, sha256
from scripts.build_submission import build
from scripts.fastchess_matches import run_game, score_summary
from scripts.magnus_benchmark import SF, manifest
from scripts.puzzle_evaluate import judge
from scripts.record_fastchess import audit_game
from training.elite_cases import CONFIG, RUN, EliteVerifier, verify_cached
from training.elite_train import fit
from training.fastchess_data import ROOT


def read(path):
    return json.loads(path.read_text())


def review_game(game, config):
    out = RUN / "reviews" / f"game-{game['id']:03}"
    board = chess.Board(game.get("start_fen", chess.STARTING_FEN))
    for uci in game["opening"]:
        board.push_uci(uci)
    start = board.fen()
    history, rows = [], []
    for index, move in enumerate(game["moves"]):
        assert board.fen() == move["fen"]
        own = move["white"] == game["candidate_white"]
        rows.append(dict(id=f"elite-adaptation:{game['id']}:{index}", source_game_id=f"elite-adaptation:{game['id']}",
                    family_id=f"elite-adaptation:{game['id']}", split="train" if own else "diagnostic",
                    solver_fen=board.fen(), played_uci=move["uci"], primary_family="actual_game_review",
                    origin_type="actual_candidate_move" if own else "actual_opponent_move",
                    training_game_score=game["score"] if own else 0.0,
                    clock_before_ms=move["clock_before_ms"], opponent_setting=game["elo"],
                    relevant_history=dict(start_fen=start, moves=list(history), complete=True)))
        board.push_uci(move["uci"])
        history.append(move["uci"])
    assert board.fen() == game["final_fen"]
    verified = verify_cached(rows, out)
    own = [row for row in verified if row["split"] == "train"]
    assessments = [dict(id=row["id"], played=row["played_uci"], assessment=judge(row, row["played_uci"])) for row in own]
    save_json(out / "review.json", dict(status="complete", game_id=game["id"], result=game["score"],
              game_sha256=sha256(RUN / "adaptation" / f"game-{game['id']:03}.json"),
              all_moves_attempted=len(rows), all_moves_verified=len(verified), own_verified=len(own),
              own_move_assessments=assessments,
              verified_own_blunders=sum(r["assessment"].get("blunder") is True for r in assessments),
              scope="Every recorded ply independently reviewed. Unstable/mate-scored/draw-history-limited roots are recorded as unresolved, never as zero error. Only the candidate's verified moves enter this adaptation update."))
    return own


def package(baseline, policy, name, index):
    folder = ROOT / "candidates" / name
    if folder.exists():
        assert sha256(folder / "models/player-policy.npz") == sha256(policy)
    else:
        shutil.copytree(ROOT / baseline, folder, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copy2(policy, folder / "models/player-policy.npz")
    base_files, copied_files = manifest(ROOT / baseline), manifest(folder)
    base_files.pop("models/player-policy.npz")
    copied_files.pop("models/player-policy.npz")
    assert base_files == copied_files, "All non-policy runtime bytes must match the preserved best"
    report = read(folder.with_suffix(".manifest.json")) if folder.with_suffix(".zip").exists() else build(folder, folder.with_suffix(".zip"))
    assert sha256(folder.with_suffix(".zip")) == report["sha256"]
    check = RUN / "runtime-checks" / f"{name}.json"
    check.parent.mkdir(exist_ok=True)
    if not check.exists():
        subprocess.run([sys.executable, "-m", "scripts.validate_package", "--zip", str(folder.with_suffix(".zip")),
                        "--calls", "3", "--clock-ms", "1000", "--out", str(check)], cwd=ROOT, check=True,
                       stdout=subprocess.DEVNULL, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    validation = read(check)
    assert validation["sha256"] == report["sha256"] and all(value == "blocked" for value in validation["read_only_checks"].values())
    registry_path = RUN / "candidate-index.json"
    registry = read(registry_path) if registry_path.exists() else []
    previous = [row for row in registry if row["candidate"] == folder.relative_to(ROOT).as_posix()]
    if previous:
        assert len(previous) == 1 and previous[0]["sha256"] == report["sha256"]
    else:
        registry.append(dict(candidate=folder.relative_to(ROOT).as_posix(), public_version=f"v1.{index}",
                         sha256=report["sha256"], policy_sha256=sha256(policy), zip_bytes=report["zip_bytes"],
                         status="experimental pending fixed final comparison", created_utc=datetime.now(timezone.utc).isoformat()))
    save_json(registry_path, registry)
    return folder.relative_to(ROOT).as_posix()


def fixed_matches(label, jobs, config):
    out = RUN / label
    paths = {job["candidate_path"] for job in jobs} | {job["opponent_path"] for job in jobs if "opponent_path" in job}
    frozen = {path: manifest(ROOT / path) for path in paths}
    sources = {name: sha256(ROOT / name) for name in ["scripts/elite_learning_session.py", "scripts/fastchess_matches.py", "harness/sandbox.py"]}
    report = dict(status="running", config=config, schedule=jobs, games=[], files=frozen, source_files=sources,
                  stockfish_sha256=sha256(SF), started_utc=datetime.now(timezone.utc).isoformat())
    result_path = out / "results.json"
    if result_path.exists():
        previous = read(result_path)
        for key in ["config", "schedule", "files", "source_files", "stockfish_sha256"]:
            assert previous[key] == report[key], f"Frozen match resume mismatch: {key}"
        if previous["status"] == "complete":
            return previous
        report = previous
        report.update(status="running")
        report.pop("error", None)
    else:
        out.mkdir(parents=True)
    complete = {row["id"]: row for row in report["games"]}
    for job in jobs:
        path = out / f"game-{job['id']:03}.json"
        if path.exists() and job["id"] not in complete:
            row = read(path)
            assert all(row[key] == value for key, value in job.items())
            complete[job["id"]] = row
    report["games"] = list(complete.values())
    save_json(result_path, report)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=config["workers"]) as pool:
            futures = [pool.submit(run_game, job, config, out) for job in jobs if job["id"] not in complete]
            for future in concurrent.futures.as_completed(futures):
                row = future.result()
                report["games"].append(row)
                report["games"].sort(key=lambda item: item["id"])
                report["summary"] = score_summary(report["games"])
                save_json(result_path, report)
                print(f"{label}: {len(report['games'])}/{len(jobs)} {row['family']} {row['score']} {row['termination']}", flush=True)
        assert frozen == {path: manifest(ROOT / path) for path in paths}
        for row in report["games"]:
            audit_game(row, config)
        report.update(status="complete", completed_utc=datetime.now(timezone.utc).isoformat())
    except BaseException as error:
        report.update(status="failed", error=repr(error))
        raise
    finally:
        save_json(result_path, report)
    return report


def validate_openings(openings):
    path = RUN / "evaluation-opening-audit.json"
    if path.exists():
        result = read(path)
        assert result["openings"] == openings
        return
    verifier = EliteVerifier(SF)
    rows = []
    try:
        for index, opening in enumerate(openings):
            board = chess.Board()
            for uci in opening:
                board.push_uci(uci)
            results = [verifier.analyse(board, nodes) for nodes in [80000, 320000]]
            best = [max(value["cp"] for value in result.values() if value["cp"] is not None) for result in results]
            assert max(abs(value) for value in best) <= 100, "Opening is outside the declared ±100cp balance gate; inspect before any evaluation game"
            rows.append(dict(pair=index, fen=board.fen(), root_estimates_cp=best))
    finally:
        verifier.close()
    save_json(path, dict(status="complete", openings=openings, rows=rows, teacher_sha256=sha256(SF),
              limitation="Finite estimates, not exact equality. These openings are held out from this adaptation schedule, not necessarily absent from older training histories."))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    RUN.mkdir(exist_ok=True)
    state_path = RUN / "session.json"
    config = read(CONFIG)
    state = dict(status="waiting", stage="threephase_completion", config_sha256=sha256(CONFIG),
                 started_utc=datetime.now(timezone.utc).isoformat())
    if state_path.exists():
        assert args.resume
        previous = read(state_path)
        assert previous["status"] == "failed" and previous["config_sha256"] == state["config_sha256"]
    def stage(name):
        if (ROOT / "STOP_TRAINING").exists():
            raise InterruptedError("STOP_TRAINING requested")
        state.update(status="running", stage=name, updated_utc=datetime.now(timezone.utc).isoformat())
        save_json(state_path, state)
    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    save_json(state_path, state)
    try:
        phase = ROOT / "runs/threephase-pilot-20260906"
        while not (phase / "selection.json").exists():
            current = read(phase / "final-cycle.json")
            if current["status"] == "failed":
                raise RuntimeError("Phase tests failed; preserve and inspect before elite training")
            if current["status"] == "complete":
                stage("threephase_final_audit")
                subprocess.run([sys.executable, "-m", "scripts.record_threephase"], cwd=ROOT, check=True,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                break
            if (ROOT / "STOP_TRAINING").exists():
                raise InterruptedError("STOP_TRAINING requested")
            time.sleep(5)
        selection = read(phase / "selection.json")
        assert selection["status"] == "complete"
        baseline = selection["selected_path"]
        state["baseline"] = baseline
        state["baseline_zip_sha256"] = sha256((ROOT / baseline).with_suffix(".zip"))
        stage("full_unit_tests")
        subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=ROOT, check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        stage("case_verification")
        subprocess.run([sys.executable, "-m", "training.elite_cases", "--verify"], cwd=ROOT, check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        stage("seed_training")
        policies = {name: ROOT / baseline / "models/player-policy.npz" for name in ["teacher_only", "outcome"]}
        trained = fit("seed", policies, [])
        policies = {name: ROOT / row["best_policy"] for name, row in trained["recipes"].items()}
        active = package(baseline, policies["outcome"], "elite-case-seed-v1", 25)
        reviews, adaptation = [], []
        out = RUN / "adaptation"
        out.mkdir(exist_ok=True)
        openings = read(ROOT / "configs/fastchess-openings.json")[:config["training_rounds"]]
        game_id = 0
        for round_index in range(config["training_rounds"]):
            for elo in config["training_elo_settings"]:
                for white in [True, False]:
                    game_id += 1
                    stage(f"adaptation_game_{game_id}")
                    job = dict(id=game_id, candidate_path=active, family=f"stockfish:{elo}", elo=elo,
                               pair=round_index, opening=openings[round_index], candidate_white=white)
                    frozen = manifest(ROOT / active)
                    path = out / f"game-{game_id:03}.json"
                    if path.exists():
                        game = read(path)
                        assert all(game[key] == value for key, value in job.items())
                    else:
                        game = run_game(job, config, out)
                    assert frozen == manifest(ROOT / active)
                    audit_game(game, config)
                    adaptation.append(game)
                    save_json(out / "results.json", dict(status="running", config=config, games=adaptation,
                              scope="Adaptive training games with changing checkpoints; never used as frozen strength evidence."))
                    stage(f"review_game_{game_id}")
                    reviews.append(review_game(game, config))
                    stage(f"weight_update_{game_id}")
                    trained = fit(f"after-game-{game_id:02}", policies, reviews)
                    policies = {name: ROOT / row["best_policy"] for name, row in trained["recipes"].items()}
                    active = package(baseline, policies["outcome"], f"elite-outcome-g{game_id:02}-v1", 25 + game_id)
        save_json(out / "results.json", dict(status="complete", config=config, games=adaptation,
                  scope="Adaptive training outcomes; checkpoints changed after every game and these games cannot establish a rating."))
        control = package(baseline, policies["teacher_only"], "elite-teacher-control-v1", 26 + game_id)
        frozen_selection = dict(challenger=active, control=control, baseline=baseline,
                    files={path: manifest(ROOT / path) for path in [active, control, baseline]},
                    rule="Epoch zero and incremental checkpoints selected using the fixed broad/phase/puzzle validation objective. All fresh match outcomes remain unopened.")
        freeze_path = RUN / "validation-selection.json"
        if freeze_path.exists():
            assert read(freeze_path) == frozen_selection
        else:
            save_json(freeze_path, frozen_selection)
        stage("evaluation_opening_audit")
        final_openings = read(ROOT / "configs/elite-evaluation-openings.json")
        assert len(final_openings) == config["final_pairs_per_setting"]
        validate_openings(final_openings)
        stage("fresh_confirmation")
        jobs = []
        for opponent, count in [(baseline, config["confirmation_pairs"]), (control, config["control_pairs"])]:
            for pair, opening in enumerate(final_openings[:count]):
                for white in [True, False]:
                    jobs.append(dict(id=len(jobs) + 1, candidate_path=active, opponent_path=opponent,
                                family=opponent, pair=pair, opening=opening, candidate_white=white))
        fixed_matches("confirmation", jobs, config)
        stage("fresh_2400_2600")
        jobs = []
        for elo in config["training_elo_settings"]:
            for pair, opening in enumerate(final_openings):
                for white in [True, False]:
                    jobs.append(dict(id=len(jobs) + 1, candidate_path=active, family=f"stockfish:{elo}", elo=elo,
                                pair=pair, opening=opening, candidate_white=white))
        fixed_matches("rated", jobs, config)
        state.update(status="complete", stage="awaiting_elite_final_audit")
    except BaseException as error:
        state.update(status="failed", error=repr(error))
        raise
    finally:
        state["updated_utc"] = datetime.now(timezone.utc).isoformat()
        save_json(state_path, state)
        if os.name == "nt":
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == "__main__":
    main()
