"""Run the fixed combined-candidate tests, with at most two simultaneous games."""

import argparse
import concurrent.futures
import ctypes
import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.alien_rating_ladder import save_json


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--candidate", type=Path, required=True)
    p.add_argument("--engine", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists() or Path("STOP_BENCHMARK").exists():
        raise ValueError("Use a fresh output directory and clear any intentional stop marker")
    a.out.mkdir(parents=True)
    candidate = a.candidate.resolve()
    files = {
        f.relative_to(candidate).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
        for f in candidate.rglob("*")
        if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc"
    }
    report = {
        "status": "running",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "candidate": str(candidate),
        "candidate_file_hashes": files,
        "candidate_zip_sha256": hashlib.sha256(
            candidate.with_suffix(".zip").read_bytes()
        ).hexdigest(),
        "runtime": json.loads((candidate / "runtime.json").read_text()),
        "policy_source": "candidates/witty-300k-hybrid-v1/models/player-policy.npz",
        "method": "Classical evaluation/search plus unchanged Witty-trained move policy. Bounded 10cp policy preference and 15cp optional Alien hint; no new fitting or dataset concatenation. Classical has no learned network to average.",
        "concurrent_games": 2,
        "base_ms": 30000,
        "increment_ms": 300,
        "planned_games": {"rating1700": 12, "classical_comparison": 12},
        "completed_stages": [],
    }
    save_json(a.out / "session.json", report)
    commands = {
        "rating1700": [
            sys.executable,
            "-m",
            "scripts.rating_benchmark",
            "--engine",
            str(a.engine.resolve()),
            "--agent",
            str(candidate),
            "--elos",
            "1700",
            "--pairs",
            "6",
            "--base-ms",
            "30000",
            "--increment-ms",
            "300",
            "--openings",
            "configs/mixed-benchmark-openings.json",
            "--out",
            str(a.out / "rating1700.json"),
        ],
        "classical_comparison": [
            sys.executable,
            "-m",
            "scripts.arena_compare",
            "--agent",
            str(candidate),
            "--opponent",
            "champions/classical-v2",
            "--games",
            "12",
            "--base-ms",
            "30000",
            "--increment-ms",
            "300",
            "--ply-cap",
            "400",
            "--out",
            str(a.out / "classical_comparison.json"),
        ],
    }

    def run_stage(stage):
        with (
            (a.out / f"{stage}.log").open("w") as stdout,
            (a.out / f"{stage}.errors.log").open("w") as stderr,
        ):
            subprocess.run(
                commands[stage],
                stdout=stdout,
                stderr=stderr,
                check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        result = json.loads((a.out / f"{stage}.json").read_text())
        if len(result["games"]) != 12 or result.get("status", "complete") != "complete":
            raise RuntimeError(f"Incomplete stage: {stage}")
        return stage

    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run_stage, stage) for stage in commands]
            for future in concurrent.futures.as_completed(futures):
                report["completed_stages"].append(future.result())
                report["updated_utc"] = datetime.now(timezone.utc).isoformat()
                save_json(a.out / "session.json", report)
        assert all(
            hashlib.sha256((candidate / name).read_bytes()).hexdigest() == digest
            for name, digest in files.items()
        )
        report["status"] = "complete"
    except Exception as error:
        report.update(status="failed", error=repr(error))
        raise
    finally:
        report["updated_utc"] = datetime.now(timezone.utc).isoformat()
        save_json(a.out / "session.json", report)
        if os.name == "nt":
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
