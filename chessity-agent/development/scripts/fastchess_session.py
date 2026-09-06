"""Queue the supplied-pack pilot behind the frozen comparison, then run its complete experiment."""

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
from training.fastchess_data import CONFIG, ROOT, RUN


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    path = RUN / "session.json"
    if path.exists() and not args.resume:
        raise ValueError("Preserve the existing session; inspect before resuming")
    config = json.loads(CONFIG.read_text())
    state = dict(status="queued", stage="awaiting_frozen_fusion_tests", config=config,
                 started_utc=datetime.now(timezone.utc).isoformat(), completed_stages=[],
                 initial_policy_sha256=sha256(ROOT / config["initial_policy"]))
    if args.resume:
        previous = json.loads(path.read_text())
        if previous["status"] != "failed" or previous["config"] != config:
            raise ValueError("Only resume a failed session with the same frozen experiment configuration")
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        shutil.copy2(path, RUN / f"session-before-resume-{stamp}.json")
        old_log = RUN / f"{previous['stage']}.log"
        if old_log.exists():
            shutil.copy2(old_log, RUN / f"{previous['stage']}-before-resume-{stamp}.log")
        state = previous
        state.setdefault("resumes", []).append(dict(utc=stamp, failed_stage=state["stage"],
            previous_error=state.pop("error", None), previous_source_files=state.get("source_files")))
        state.update(status="queued", stage="awaiting_frozen_fusion_tests")
    environment = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")

    def save():
        state["updated_utc"] = datetime.now(timezone.utc).isoformat()
        save_json(path, state)

    def run(stage, module, *options):
        if stage in state["completed_stages"]:
            return
        state.update(status="running", stage=stage)
        save()
        with (RUN / f"{stage}.log").open("w", encoding="utf-8") as stream:
            subprocess.run([sys.executable, "-m", module, *map(str, options)], cwd=ROOT, env=environment,
                           stdout=stream, stderr=subprocess.STDOUT, check=True,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        state["completed_stages"].append(stage)
        save()

    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    save()
    try:
        upstream_path = ROOT / "runs/final-fusion-20260906/session.json"
        while True:
            upstream = json.loads(upstream_path.read_text())
            if upstream["status"] == "complete":
                break
            if upstream["status"] == "failed":
                raise RuntimeError("Frozen upstream tests failed; inspect them before continuing")
            if (ROOT / "STOP_TRAINING").exists():
                raise InterruptedError("STOP_TRAINING requested")
            time.sleep(5)
        state["source_files"] = {str(p.relative_to(ROOT)): sha256(p) for directory in ["training", "scripts", "engine"]
                                 for p in (ROOT / directory).glob("*.py")}
        run("record-preserved-best", "scripts.record_final_fusion")
        run("unit-tests", "pytest", "-q")
        run("verify-data", "training.fastchess_data", "--stage", "verify")
        run("graph-report", "scripts.fastchess_graph_report")
        run("training", "training.fastchess_train")
        for name, recipe, adaptive in [("fastchess-control-v1", "control", True),
                                       ("fastchess-static-v1", "fastchess", False),
                                       ("fastchess-adaptive-v1", "fastchess", True)]:
            folder = ROOT / "candidates" / name
            options = ["--mode", "classical", "--player-policy", RUN / "training" / recipe / "best.npz",
                       "--policy-cp", 10, "--opening-style", "alien-selective", "--alien-cp", 15, "--out", folder]
            if adaptive:
                options += ["--adaptive-time"]
            run("build-" + name, "scripts.make_variant", *options)
            run("package-" + name, "scripts.build_submission", "--root", folder, "--out", folder.with_suffix(".zip"))
            run("validate-" + name, "scripts.validate_package", "--zip", folder.with_suffix(".zip"),
                "--out", RUN / f"validate-{name}.json")
            run("validate-active-" + name, "scripts.validate_package", "--zip", folder.with_suffix(".zip"),
                "--clock-ms", 1000, "--calls", 30, "--out", RUN / f"validate-active-{name}.json")
        run("evaluation", "scripts.fastchess_evaluate")
        run("comparison", "scripts.fastchess_matches", "--stage", "comparison")
        run("rated", "scripts.fastchess_matches", "--stage", "rated")
        run("loss-audit", "scripts.fastchess_loss_audit")
        state.update(status="complete", stage="awaiting_final_report_and_publication")
    except BaseException as error:
        state.update(status="failed", error=repr(error))
        raise
    finally:
        save()
        if os.name == "nt":
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == "__main__":
    main()
