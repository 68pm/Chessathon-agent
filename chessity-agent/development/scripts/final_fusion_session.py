"""Build, freeze and test full fusion at the user's competition clock."""

import ctypes
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

from scripts.alien_rating_ladder import save_json, sha256
from scripts.final_fusion_benchmark import AGENTS, ROOT, RUN


def main():
    if RUN.exists():
        raise ValueError("Fresh final-fusion session required")
    RUN.mkdir()
    config = json.loads((ROOT / "configs/final-fusion.json").read_text())
    state = {"status": "running", "started_utc": datetime.now(timezone.utc).isoformat(),
             "stage": "prepare", "completed_stages": [], "config": config,
             "initial_models": {name: sha256(ROOT / config[name]) for name in ["policy_model", "value_model"]}}

    def save():
        state["updated_utc"] = datetime.now(timezone.utc).isoformat()
        save_json(RUN / "session.json", state)

    def run(stage, module, *options):
        state["stage"] = stage
        save()
        with (RUN / f"{stage}.log").open("w", encoding="utf-8") as stream:
            subprocess.run([sys.executable, "-m", module, *map(str, options)], cwd=ROOT,
                           stdout=stream, stderr=subprocess.STDOUT, check=True,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        state["completed_stages"].append(stage)
        save()

    save()
    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        run("unit-tests", "pytest", "-q")
        for name, mode, policy_cp in [("fusion-hybrid", "hybrid", 10), ("fusion-root", "classical", 15)]:
            options = ["--mode", mode, "--model", config["value_model"], "--player-policy", config["policy_model"],
                       "--policy-cp", policy_cp, "--opening-style", "alien-selective", "--alien-cp", 15,
                       "--out", AGENTS[name]]
            if name == "fusion-root":
                options += ["--root-value", "--root-value-cp", 5]
            run("build-" + name, "scripts.make_variant", *options)
        for name, path in AGENTS.items():
            if not path.with_suffix(".zip").exists():
                run("package-" + name, "scripts.build_submission", "--root", path,
                    "--out", path.with_suffix(".zip"))
            run("validate-" + name, "scripts.validate_package", "--zip", path.with_suffix(".zip"),
                "--out", RUN / f"validate-{name}.json")
            if name.startswith("fusion"):
                run("validate-active-" + name, "scripts.validate_package", "--zip", path.with_suffix(".zip"),
                    "--clock-ms", 1000, "--calls", 30, "--out", RUN / f"validate-active-{name}.json")
        run("comparison", "scripts.final_fusion_benchmark", "--stage", "comparison")
        selection = json.loads((RUN / "selection.json").read_text())
        run("validate-selected-real-clock", "scripts.validate_package", "--zip",
            AGENTS[selection["selected_name"]].with_suffix(".zip"), "--clock-ms", 120000,
            "--calls", 2, "--out", RUN / "validate-selected-real-clock.json")
        run("rated", "scripts.final_fusion_benchmark", "--stage", "rated")
        assert selection["selected_zip_sha256"] == sha256(AGENTS[selection["selected_name"]].with_suffix(".zip"))
        selection["status"] = "complete"
        selection["rated_results"] = "runs/final-fusion-20260906/rated/results.json"
        selection["completed_utc"] = datetime.now(timezone.utc).isoformat()
        save_json(RUN / "selection.json", selection)
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
