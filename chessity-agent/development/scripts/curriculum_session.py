"""Wait for the frozen benchmark, then run the documented small curriculum pilot."""

import ctypes
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.alien_rating_ladder import save_json

RUN = Path("runs/carlsen-curriculum-20260906")


def main():
    if RUN.exists():
        raise ValueError("Fresh curriculum session required")
    RUN.mkdir()
    state = {
        "status": "running",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "stage": "waiting-for-frozen-magnus-benchmark",
        "completed_stages": [],
    }

    def save():
        state["updated_utc"] = datetime.now(timezone.utc).isoformat()
        save_json(RUN / "session.json", state)

    def run(stage, module, *options):
        state["stage"] = stage
        save()
        with (RUN / f"{stage}.log").open("w", encoding="utf-8") as log:
            subprocess.run(
                [sys.executable, "-m", module, *map(str, options)],
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        state["completed_stages"].append(stage)
        save()

    save()
    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        while True:
            baseline = json.loads(
                Path("runs/magnus-mixed-20260906/benchmark/results.json").read_text()
            )
            if baseline["status"] == "complete":
                break
            if baseline["status"] != "running":
                raise RuntimeError("Baseline benchmark did not complete")
            time.sleep(10)
        run("record-magnus", "scripts.record_magnus_session")
        run("prepare", "training.chess_curriculum", "--out", RUN / "data")
        run("train", "training.curriculum_pilot", "--data", RUN / "data", "--out", RUN / "training")
        run(
            "diagnostics",
            "scripts.curriculum_diagnostics",
            "--training",
            RUN / "training",
            "--out",
            RUN / "diagnostics.json",
        )
        for recipe, name in [
            ("control", "carlsen-curriculum-control-v1"),
            ("curriculum", "carlsen-curriculum-v1"),
        ]:
            candidate = Path("candidates") / name
            run(
                "build-" + recipe,
                "scripts.make_variant",
                "--mode",
                "classical",
                "--player-policy",
                RUN / f"training/{recipe}/best.npz",
                "--policy-cp",
                10,
                "--opening-style",
                "alien-selective",
                "--alien-cp",
                15,
                "--out",
                candidate,
            )
            run(
                "package-" + recipe,
                "scripts.build_submission",
                "--root",
                candidate,
                "--out",
                candidate.with_suffix(".zip"),
            )
            run(
                "validate-" + recipe,
                "scripts.validate_package",
                "--zip",
                candidate.with_suffix(".zip"),
                "--out",
                RUN / f"validate-{recipe}.json",
            )
            run(
                "validate-active-" + recipe,
                "scripts.validate_package",
                "--zip",
                candidate.with_suffix(".zip"),
                "--clock-ms",
                1000,
                "--calls",
                30,
                "--out",
                RUN / f"validate-active-{recipe}.json",
            )
        run("benchmark", "scripts.curriculum_benchmark")
        run("record", "scripts.record_curriculum_session")
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
