"""Phase-resolved move quality at fixed nodes and actual remaining-clock inputs."""

import argparse
import json
import os
import shutil
import subprocess
import sys
from collections import Counter

import numpy as np

from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import manifest
from scripts.puzzle_evaluate import judge
from scripts.threephase_matches import CONFIG, RUN
from training.fastchess_data import ROOT, read_rows


def summarize(rows):
    groups = {}
    for mode in sorted({r["mode"] for r in rows}):
        for phase in ["all", "opening", "middlegame", "transition", "endgame"]:
            part = [r for r in rows if r["mode"] == mode and (phase == "all" or r["phase"] == phase)]
            if not part:
                continue
            cp = [r for r in part if r["assessment"].get("regret_cp") is not None]
            groups[f"{mode}:{phase}"] = dict(positions=len(part), accepted=sum(r["assessment"]["accepted"] for r in part),
                illegal=sum(not r["assessment"]["legal"] for r in part),
                clock_overruns=sum(r["clock_ms"] is not None and r["seconds"] * 1000 >= r["clock_ms"] for r in part),
                cp_positions=len(cp), blunders=sum(r["assessment"]["blunder"] for r in cp),
                mean_regret_cp=float(np.mean([r["assessment"]["regret_cp"][1] for r in cp])) if cp else None,
                median_seconds=float(np.median([r["seconds"] for r in part])),
                p95_seconds=float(np.percentile([r["seconds"] for r in part], 95)),
                median_nodes=float(np.median([r["nodes"] for r in part])),
                completed_depths=dict(Counter(r["depth"] for r in part if r["depth"] is not None)))
    return groups


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--split", choices=["train", "validation", "test"], required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text())
    candidate = ROOT / args.candidate
    if args.split == "test":
        selection = json.loads((RUN / "validation-selection.json").read_text())
        assert args.candidate in {selection["challenger"], config["baseline"], config["previous_newest"]}
    manifest_data = json.loads((RUN / "data/manifest.json").read_text())
    assert sha256(RUN / "data/verified.jsonl") == manifest_data["verified_sha256"]
    tasks = [r for r in read_rows(RUN / "data/verified.jsonl") if r["split"] == args.split]
    assert tasks
    out = RUN / "evaluation" / args.split / candidate.name
    if out.exists() and not args.resume:
        raise ValueError("Preserve existing evaluation results")
    out.mkdir(parents=True, exist_ok=args.resume)
    # The child sees only ID, board and history; hide identity, result, phase and teacher labels.
    task_path = out / "inputs.json"
    save_json(task_path, [{k: r[k] for k in ["id", "solver_fen", "relevant_history"]} for r in tasks])
    by_id = {r["id"]: r for r in tasks}
    frozen = manifest(candidate)
    env = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")
    report = dict(status="running", candidate=args.candidate, split=args.split, files=frozen,
                  dataset_sha256=manifest_data["verified_sha256"], rows=[],
                  source_files={p: sha256(ROOT / p) for p in ["scripts/threephase_evaluate.py", "scripts/threephase_probe.py"]},
                  scope="Direct saved-agent calls with full reconstructed history; clock includes get_move but excludes transport. Multiple modes reuse the same positions, not independent samples. No external teacher used at inference.")
    if args.resume and (out / "results.json").exists():
        previous = json.loads((out / "results.json").read_text())
        for key in ["candidate", "split", "files", "dataset_sha256", "source_files"]:
            assert previous[key] == report[key], key
        if previous["status"] == "complete":
            print("This frozen position assessment is already complete.")
            return
        report = previous
    save_json(out / "results.json", report)
    for mode, options in [("nodes2000", ["--nodes", "2000"]), ("clock4000", ["--clock-ms", "4000"]),
                          ("clock800", ["--clock-ms", "800"]),
                          ("nodes2000_book_off", ["--nodes", "2000", "--disable-opening"])]:
        probe_path = out / f"{mode}.json"
        recorded = [row for row in report["rows"] if row["mode"] == mode]
        if recorded:
            assert len(recorded) == len(tasks) and {r["id"] for r in recorded} == set(by_id)
            continue
        if probe_path.exists():
            backup = out / f"{mode}.before-resume-{len(list(out.glob(mode + '.before-resume-*')))}.json"
            shutil.copy2(probe_path, backup)
        subprocess.run([sys.executable, "-m", "scripts.threephase_probe", "--agent", str(candidate),
                        "--tasks", str(task_path), "--out", str(probe_path), *options],
                       cwd=ROOT, env=env, check=True, creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        answers = json.loads(probe_path.read_text())
        assert len(answers) == len(tasks)
        for answer in answers:
            row = by_id[answer["id"]]
            report["rows"].append(dict(**answer, phase=row["primary_phase"], mode=mode,
                                       assessment=judge(row, answer["uci"])))
        report["summary"] = summarize(report["rows"])
        save_json(out / "results.json", report)
        print(f"{args.split}:{candidate.name}:{mode} complete ({len(tasks)} positions)", flush=True)
    assert frozen == manifest(candidate)
    report["status"] = "complete"
    save_json(out / "results.json", report)


if __name__ == "__main__":
    main()
