"""Run the frozen final phase tests sequentially after validation-only selection."""

import argparse
import ctypes
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone

from scripts.alien_rating_ladder import save_json, sha256
from scripts.threephase_matches import CONFIG, RUN
from training.fastchess_data import ROOT


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    selection = json.loads((RUN / "validation-selection.json").read_text())
    config = json.loads(CONFIG.read_text())
    challenger = selection["challenger"]
    path = RUN / "final-cycle.json"
    state = dict(status="running", completed_stages=[], challenger=challenger,
                 selection_sha256=sha256(RUN / "validation-selection.json"),
                 started_utc=datetime.now(timezone.utc).isoformat())
    if path.exists():
        assert args.resume
        previous = json.loads(path.read_text())
        assert previous["status"] == "failed" and previous["selection_sha256"] == state["selection_sha256"]
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        shutil.copy2(path, RUN / f"final-cycle-before-resume-{stamp}.json")
        state = previous
        state.setdefault("resumes", []).append(dict(utc=stamp, error=state.pop("error", None)))
    environment = dict(os.environ, OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1", MKL_NUM_THREADS="1")

    def save():
        state["updated_utc"] = datetime.now(timezone.utc).isoformat()
        save_json(path, state)

    def run(stage, module, *options):
        if stage in state["completed_stages"]:
            return
        if (ROOT / "STOP_TRAINING").exists():
            raise InterruptedError("STOP_TRAINING requested")
        state.update(status="running", stage=stage)
        state.setdefault("stage_source_sha256", {})[stage] = sha256(ROOT / (module.replace(".", "/") + ".py"))
        save()
        if args.resume and module in {"scripts.threephase_evaluate", "scripts.threephase_matches", "scripts.threephase_endgames"}:
            options = (*options, "--resume")
        with (RUN / f"{stage}.log").open("a" if args.resume else "w", encoding="utf-8") as stream:
            subprocess.run([sys.executable, "-m", module, *options], cwd=ROOT, env=environment,
                           stdout=stream, stderr=subprocess.STDOUT, check=True,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        state["completed_stages"].append(stage)
        save()

    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        for candidate in dict.fromkeys([config["baseline"], challenger]):
            run(f"test-{candidate.split('/')[-1]}", "scripts.threephase_evaluate", "--split", "test", "--candidate", candidate)
        run("final-confirmation", "scripts.threephase_matches", "--stage", "confirmation", "--candidate", challenger)
        run("final-rated", "scripts.threephase_matches", "--stage", "rated", "--candidate", challenger)
        for candidate in dict.fromkeys([config["baseline"], challenger]):
            run(f"endgames-{candidate.split('/')[-1]}", "scripts.threephase_endgames", "--candidate", candidate)
        state.update(status="complete", stage="awaiting_final_audit")
    except BaseException as error:
        state.update(status="failed", error=repr(error))
        raise
    finally:
        save()
        if os.name == "nt":
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == "__main__":
    main()
