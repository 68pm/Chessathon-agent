"""Complete the authorised history, policy training, legality checks and strength games."""

import argparse
import ctypes
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from training.history_batches import load_json, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--engine", type=Path, required=True)
    parser.add_argument("--authorisation-reference", required=True)
    parser.add_argument("--out", type=Path, default=Path("runs/witty-style-20260906"))
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    args.out.mkdir(parents=True, exist_ok=True)
    state = {
        "status": "running",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "completed_stages": [],
        "authorisation": args.authorisation_reference,
    }

    def save():
        state["updated_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(args.out / "session-status.json", state)

    def run(stage, module, *options):
        state["stage"] = stage
        save()
        print(f"Starting {stage}", flush=True)
        with (args.out / f"{stage}.log").open("w", encoding="utf-8") as log:
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
        history = Path("data/witty_alien-history")
        run(
            "history",
            "training.history_batches",
            "--player",
            "witty_alien",
            "--out",
            history,
            "--authorisation-reference",
            args.authorisation_reference,
            "--preparation-workers",
            4,
            "--scratch",
            "../../work/witty-history-prep-20260906",
        )
        snapshot = history / load_json(history / "latest.json")["export"]
        state["history_export"] = str(snapshot)
        policy = args.out / "policy"
        run(
            "train-policy",
            "training.player_policy",
            "--samples",
            snapshot / "style-samples.jsonl",
            "--out",
            policy,
            "--epochs",
            12,
        )
        candidate = Path("candidates/witty-300k-hybrid-v1")
        run(
            "build-candidate",
            "scripts.make_variant",
            "--mode",
            "hybrid",
            "--model",
            "models/value-300k.npz",
            "--player-policy",
            policy / "best.npz",
            "--policy-cp",
            20,
            "--opening-style",
            "alien",
            "--out",
            candidate,
        )
        run(
            "package",
            "scripts.build_submission",
            "--root",
            candidate,
            "--out",
            candidate.with_suffix(".zip"),
        )
        run(
            "validate",
            "scripts.validate_package",
            "--zip",
            candidate.with_suffix(".zip"),
            "--out",
            args.out / "package-validation.json",
        )
        run(
            "validate-active-policy",
            "scripts.validate_package",
            "--zip",
            candidate.with_suffix(".zip"),
            "--clock-ms",
            1000,
            "--calls",
            30,
            "--out",
            args.out / "active-policy-validation.json",
        )
        run(
            "comparison",
            "scripts.arena_compare",
            "--agent",
            candidate,
            "--opponent",
            "runs/unattended-20260905-away/candidate-300000-hybrid",
            "--games",
            12,
            "--base-ms",
            3000,
            "--increment-ms",
            50,
            "--out",
            args.out / "comparison.json",
        )
        run(
            "rating",
            "scripts.rating_benchmark",
            "--engine",
            args.engine,
            "--agent",
            candidate,
            "--pairs",
            6,
            "--base-ms",
            30000,
            "--increment-ms",
            300,
            "--out",
            args.out / "rating.json",
        )
        state["status"] = "complete"
    except BaseException as error:
        state["status"], state["error"] = "failed", repr(error)
        raise
    finally:
        save()
        if os.name == "nt":
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == "__main__":
    main()
