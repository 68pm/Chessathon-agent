"""Run the frozen verified-puzzle pilot through training, package checks and paired games."""

import ctypes
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.alien_rating_ladder import save_json

RUN = Path("runs/puzzle-pilot-20260906")


def main():
    state = {"status": "running", "started_utc": datetime.now(timezone.utc).isoformat(),
             "stage": "waiting-for-data", "completed_stages": []}

    def save():
        state["updated_utc"] = datetime.now(timezone.utc).isoformat()
        save_json(RUN / "session.json", state)

    def run(stage, module, *options):
        state["stage"] = stage
        save()
        with (RUN / f"{stage}.log").open("w", encoding="utf-8") as stream:
            subprocess.run([sys.executable, "-m", module, *map(str, options)],
                           stdout=stream, stderr=subprocess.STDOUT, check=True,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        state["completed_stages"].append(stage)
        save()

    if (RUN / "session.json").exists():
        raise ValueError("Session already exists; inspect before resuming individual stages")
    save()
    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        deadline = time.monotonic() + 1800
        while not (RUN / "data/manifest.json").exists():
            if time.monotonic() > deadline:
                raise TimeoutError("Data verification did not finish within 30 minutes")
            time.sleep(5)
        run("audit", "scripts.audit_puzzle_data", "--data", RUN / "data")
        run("train", "training.puzzle_train", "--data", RUN / "data", "--out", RUN / "training")
        for recipe in ["control", "puzzle"]:
            candidate = Path("candidates") / ("puzzle-control-v1" if recipe == "control" else "puzzle-mixed-v1")
            run("build-" + recipe, "scripts.make_variant", "--mode", "classical", "--player-policy",
                RUN / f"training/{recipe}/best.npz", "--policy-cp", 10, "--opening-style", "alien-selective",
                "--alien-cp", 15, "--out", candidate)
            run("package-" + recipe, "scripts.build_submission", "--root", candidate,
                "--out", candidate.with_suffix(".zip"))
            run("validate-" + recipe, "scripts.validate_package", "--zip", candidate.with_suffix(".zip"),
                "--out", RUN / f"validate-{recipe}.json")
            run("validate-active-" + recipe, "scripts.validate_package", "--zip", candidate.with_suffix(".zip"),
                "--clock-ms", 1000, "--calls", 30, "--out", RUN / f"validate-active-{recipe}.json")
        run("evaluate", "scripts.puzzle_evaluate", "--data", RUN / "data", "--out", RUN / "evaluation.json",
            "--agent", "baseline=candidates/classical-witty-magnus-v1",
            "--agent", "control=candidates/puzzle-control-v1", "--agent", "puzzle=candidates/puzzle-mixed-v1")
        for name, opponent in [("baseline", "classical-witty-magnus-v1"), ("control", "puzzle-control-v1")]:
            run("matches-" + name, "scripts.arena_compare", "--agent", "candidates/puzzle-mixed-v1",
                "--opponent", "candidates/" + opponent, "--games", 8, "--base-ms", 30000,
                "--increment-ms", 300, "--ply-cap", 400, "--out", RUN / f"matches-{name}.json")
        state["status"] = "complete"
    except BaseException as error:
        state.update(status="failed", error=repr(error))
        raise
    finally:
        save()
        if os.name == "nt":
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == "__main__":
    main()
