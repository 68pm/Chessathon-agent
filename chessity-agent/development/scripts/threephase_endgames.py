"""Full endgame conversion and practical draw-preservation games against serious resistance."""

import argparse
import concurrent.futures
import json
from collections import Counter

import chess

from scripts.alien_rating_ladder import save_json, sha256
from scripts.fastchess_matches import run_game
from scripts.magnus_benchmark import manifest
from scripts.threephase_matches import CONFIG, RUN
from training.fastchess_data import ROOT, read_rows
from training.puzzle_data import digest
from training.puzzle_verifier import duplicate_key


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    config_path = ROOT / "configs/threephase-endgame-tests.json"
    config = json.loads(config_path.read_text())
    experiment = json.loads(CONFIG.read_text())
    selection = json.loads((RUN / "validation-selection.json").read_text())
    assert args.candidate in {selection["challenger"], experiment["baseline"]}
    folder = ROOT / args.candidate
    out = RUN / "endgames" / folder.name
    jobs = []
    for index, fen in enumerate(config["basic_conversion_fens"]):
        board = chess.Board(fen)
        assert board.is_valid() and not board.is_game_over()
        for mirrored in [False, True]:
            start = board.mirror() if mirrored else board
            jobs.append(dict(family=f"basic_conversion_{index}", pair=index, candidate_white=start.turn,
                             start_fen=start.fen(), source_kind="constructed_material_family_drill",
                             mirrored=mirrored, intended_objective="complete_checkmate_without_stalemate_or_time_loss"))
    practical = []
    for row in read_rows(RUN / "data/verified.jsonl"):
        if row["split"] != "test" or row["primary_phase"] != "endgame" or row["confidence"] != "engine_supported":
            continue
        board = chess.Board(row["solver_fen"])
        if board.halfmove_clock >= 40:
            continue
        if all(abs(max(value["cp"] for value in analysis.values())) <= config["practical_max_abs_cp_both_budgets"]
               for analysis in row["candidate_moves"]):
            practical.append(row)
    selected, families = [], set()
    for row in sorted(practical, key=lambda r: digest(r["id"])):
        if row["family_id"] not in families:
            selected.append(row)
            families.add(row["family_id"])
        if len(selected) == config["practical_near_equal_cases"]:
            break
    for index, row in enumerate(selected):
        jobs.append(dict(family="practical_near_equal", pair=index, candidate_white=chess.Board(row["solver_fen"]).turn,
                         start_fen=row["solver_fen"], source_id=row["id"], source_kind="heldout_game_finite_equality_estimate",
                         canonical_key=duplicate_key(chess.Board(row["solver_fen"])),
                         intended_objective="preserve_draw_or_win_against_2600_setting"))
    jobs = [dict(id=index + 1, candidate_path=args.candidate, opening=[], elo=config["opponent_elo"], **job)
            for index, job in enumerate(jobs)]
    frozen = manifest(folder)
    report = dict(status="running", candidate=args.candidate, config=config, config_sha256=sha256(config_path),
                  files=frozen, schedule=jobs, games=[], practical_cases_available=len(selected),
                  history_scope="Each game begins with the recorded FEN's rule counters and fresh repetition history, as for a curated match start.",
                  source_files={p: sha256(ROOT / p) for p in ["scripts/threephase_endgames.py", "scripts/fastchess_matches.py"]})
    if out.exists():
        assert args.resume, "Preserve completed or interrupted phase games; inspect before --resume"
        previous = json.loads((out / "results.json").read_text())
        for key in ["candidate", "config", "config_sha256", "files", "schedule", "source_files"]:
            assert report[key] == previous[key], f"Resume mismatch: {key}"
        if previous["status"] == "complete":
            print("Endgame stage already complete.")
            return
        report = previous
        report.update(status="running")
        report.pop("error", None)
    else:
        out.mkdir(parents=True)
    completed = {row["id"]: row for row in report["games"]}
    for job in jobs:
        game_path = out / f"game-{job['id']:03}.json"
        if game_path.exists() and job["id"] not in completed:
            row = json.loads(game_path.read_text())
            assert all(row[key] == value for key, value in job.items())
            completed[job["id"]] = row
    report["games"] = sorted(completed.values(), key=lambda row: row["id"])
    save_json(out / "results.json", report)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=config["workers"]) as pool:
            futures = [pool.submit(run_game, job, config, out) for job in jobs if job["id"] not in completed]
            for future in concurrent.futures.as_completed(futures):
                row = future.result()
                report["games"].append(row)
                save_json(out / "results.json", report)
                print(f"endgames:{folder.name} {len(report['games'])}/{len(jobs)} {row['family']} {row['score']}", flush=True)
        assert frozen == manifest(folder)
        report.update(status="complete", summary={
            "basic_conversion": dict(Counter(r["termination"] if r["score"] == 1 else f"not_converted:{r['termination']}"
                                             for r in report["games"] if r["source_kind"] == "constructed_material_family_drill")),
            "practical_results": dict(Counter(str(r["score"]) for r in report["games"] if r["family"] == "practical_near_equal"))})
    except BaseException as error:
        report.update(status="failed", error=repr(error))
        raise
    finally:
        save_json(out / "results.json", report)


if __name__ == "__main__":
    main()
