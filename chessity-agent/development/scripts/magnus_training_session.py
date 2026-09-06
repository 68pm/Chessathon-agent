"""Fit and package the Magnus/Witty move network with classical search."""

import ctypes
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from training.history_batches import load_json, write_json

RUN = Path("runs/magnus-mixed-20260906")
CANDIDATE = Path("candidates/classical-witty-magnus-v1")


def main():
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--resume", action="store_true")
    a = p.parse_args()
    RUN.mkdir(parents=True, exist_ok=True)
    if (RUN / "training-session.json").exists() and not a.resume:
        raise ValueError("Training session already exists; inspect before rerunning")
    state = {
        "status": "running",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "completed_stages": [],
    }
    if a.resume:
        state = load_json(RUN / "training-session.json")
        if state["status"] != "failed":
            raise ValueError("Only an inspected failed session can be resumed")
        state["previous_error"] = state.pop("error", None)
        state["status"] = "running"

    def save():
        state["updated_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(RUN / "training-session.json", state)

    def run(stage, module, *options):
        if stage in state["completed_stages"]:
            return
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

    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        state["stage"] = "waiting-for-history-analysis"
        save()
        deadline = time.monotonic() + 1800
        while True:
            history = load_json(Path("data/magnuscarlsen-history/download-status.json"))
            if history["status"].startswith("complete"):
                break
            if history["status"] != "running" or time.monotonic() > deadline:
                raise RuntimeError(f"History not ready: {history['status']}")
            time.sleep(10)
        run("mix-data", "training.mixed_player_samples", "--out", RUN / "mixture")
        run(
            "train-policy",
            "training.player_policy",
            "--samples",
            RUN / "mixture/samples.jsonl",
            "--out",
            RUN / "policy",
            "--epochs",
            12,
            "--learning-rate",
            0.0003,
            "--initial-policy",
            "candidates/mixed-classical-witty-v1/models/player-policy.npz",
            "--runtime-context",
            "Classical evaluator/search; newly fitted Magnus/Witty move policy; optional Alien hints",
        )
        run(
            "build-candidate",
            "scripts.make_variant",
            "--mode",
            "classical",
            "--player-policy",
            RUN / "policy/best.npz",
            "--policy-cp",
            10,
            "--opening-style",
            "alien-selective",
            "--alien-cp",
            15,
            "--out",
            CANDIDATE,
        )
        run(
            "package",
            "scripts.build_submission",
            "--root",
            CANDIDATE,
            "--out",
            CANDIDATE.with_suffix(".zip"),
        )
        run(
            "validate",
            "scripts.validate_package",
            "--zip",
            CANDIDATE.with_suffix(".zip"),
            "--out",
            RUN / "package-validation.json",
        )
        run(
            "validate-active",
            "scripts.validate_package",
            "--zip",
            CANDIDATE.with_suffix(".zip"),
            "--clock-ms",
            1000,
            "--calls",
            30,
            "--out",
            RUN / "active-validation.json",
        )
        state["status"] = "complete"
    except BaseException as error:
        state.update(status="failed", error=repr(error))
        raise
    finally:
        save()
        if os.name == "nt":
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
    print(json.dumps(state, indent=2))


if __name__ == "__main__":
    main()
