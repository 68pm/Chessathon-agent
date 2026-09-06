"""Continue the first measured cycle after baseline games, preserving every completed stage."""

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone

from scripts.alien_rating_ladder import save_json, sha256
from scripts.threephase_matches import CONFIG, RUN
from training.fastchess_data import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    path = RUN / "first-cycle.json"
    if path.exists() and not args.resume:
        raise ValueError("Preserve the existing controller state and inspect before resuming")
    state = dict(status="waiting", stage="baseline", completed_stages=[],
                 started_utc=datetime.now(timezone.utc).isoformat(), config_sha256=sha256(CONFIG))
    if args.resume:
        previous = json.loads(path.read_text())
        assert previous["status"] == "failed" and previous["config_sha256"] == state["config_sha256"]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        shutil.copy2(path, RUN / f"first-cycle-before-resume-{stamp}.json")
        state = previous
        state.setdefault("resumes", []).append(dict(utc=stamp, error=state.pop("error", None), stage=state["stage"]))
    environment = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")

    def save():
        state["updated_utc"] = datetime.now(timezone.utc).isoformat()
        save_json(path, state)

    def run(stage, module, *options):
        if stage in state["completed_stages"]:
            return
        state.update(status="running", stage=stage)
        state.setdefault("stage_sources", {})[stage] = {
            str(p.relative_to(ROOT)): sha256(p)
            for directory in ["engine", "scripts", "training", "tests"]
            for p in (ROOT / directory).glob("*.py")
        }
        save()
        if args.resume and (RUN / f"{stage}.log").exists():
            shutil.copy2(RUN / f"{stage}.log", RUN / f"{stage}-before-resume-{stamp}.log")
        if args.resume and module in {"scripts.threephase_evaluate", "scripts.threephase_matches"}:
            options = (*options, "--resume")
        with (RUN / f"{stage}.log").open("w", encoding="utf-8") as stream:
            subprocess.run([sys.executable, "-m", module, *options], cwd=ROOT, env=environment,
                           stdout=stream, stderr=subprocess.STDOUT, check=True,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        state["completed_stages"].append(stage)
        save()

    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    save()
    try:
        while True:
            baseline = json.loads((RUN / "baseline/results.json").read_text())
            if baseline["status"] == "complete":
                break
            if baseline["status"] == "failed":
                raise RuntimeError("Baseline failed; inspect and preserve results")
            if (ROOT / "STOP_TRAINING").exists():
                raise InterruptedError("STOP_TRAINING requested")
            time.sleep(5)
        run("full-unit-tests", "pytest", "-q")
        run("teacher-verification", "training.threephase_data", "--stage", "verify")
        for split in ["train", "validation"]:
            for candidate in ["candidates/classical-witty-magnus-v1", "candidates/threephase-pvs-v1"]:
                run(f"positions-{split}-{candidate.split('/')[-1]}", "scripts.threephase_evaluate",
                    "--split", split, "--candidate", candidate)
        run("development-pvs", "scripts.threephase_matches", "--stage", "development", "--candidate", "candidates/threephase-pvs-v1")
        state.update(status="complete", stage="awaiting_second_candidate_assessment")
    except BaseException as error:
        state.update(status="failed", error=repr(error))
        raise
    finally:
        save()
        if os.name == "nt":
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == "__main__":
    main()
