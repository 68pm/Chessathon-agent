"""Bounded local training supervisor. Never uploads; preserves the selected runtime."""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--minutes", type=int, default=60)
    p.add_argument("--run-id", default=datetime.now().strftime("%Y%m%d-%H%M%S"))
    a = p.parse_args()
    os.chdir(ROOT)
    run = ROOT / "runs" / f"unattended-{a.run_id}"
    run.mkdir(parents=True, exist_ok=False)
    deadline = time.monotonic() + a.minutes * 60
    env = os.environ.copy()
    env.update({key: "1" for key in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]})
    events = []
    current = "Starting"

    def status(state, detail):
        record = {
            "state": state,
            "detail": detail,
            "updated_utc": datetime.now(timezone.utc).isoformat(),
            "pid": os.getpid(),
            "run_directory": str(run),
            "events": events,
            "deadline_minutes": a.minutes,
            "champion": "classical-v2 (preserved)",
            "submission_policy": "Candidates are packaged separately. No upload or automatic replacement.",
        }
        (run / "status.json").write_text(json.dumps(record, indent=2))
        remaining = max(0, (deadline - time.monotonic()) / 60)
        (ROOT / "TRAINING_STATUS.md").write_text(
            f"# Unattended training\n\n**{state}** — {detail}\n\n"
            f"Updated UTC: {record['updated_utc']}\n\n"
            f"Run folder: `{run.relative_to(ROOT)}`\n\n"
            f"Remaining budget at this update: {remaining:.1f} minutes.\n\n"
            "The selected submission remains classical-v2. Candidates, metrics and checkpoints "
            "are saved separately. No paid compute or uploads.\n\n"
            "To stop: create `STOP_TRAINING` in the project folder. The supervisor checks "
            "within one second and stops its active training subprocess. Completed checkpoints survive.\n\n"
            "Read the run status.json and numbered logs for detailed progress.\n",
            encoding="utf-8",
        )

    def execute(name, module, *args):
        nonlocal current
        current = name
        if (ROOT / "STOP_TRAINING").exists():
            raise InterruptedError("STOP_TRAINING requested")
        if time.monotonic() >= deadline:
            raise TimeoutError("One-hour training budget reached")
        status("RUNNING", name)
        command = [sys.executable, "-u", "-m", module, *map(str, args)]
        logfile = run / f"{len(events):02d}-{name}.log"
        started = time.monotonic()
        with logfile.open("w", encoding="utf-8") as output:
            child = subprocess.Popen(
                command,
                cwd=ROOT,
                env=env,
                stdout=output,
                stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            try:
                while child.poll() is None:
                    if (ROOT / "STOP_TRAINING").exists():
                        raise InterruptedError("STOP_TRAINING requested")
                    if time.monotonic() >= deadline:
                        raise TimeoutError("Training budget reached")
                    time.sleep(1)
            finally:
                if child.poll() is None:
                    child.terminate()
                    child.wait(timeout=10)
            if child.returncode:
                raise RuntimeError(f"{name} exited {child.returncode}; see {logfile.name}")
        events.append(
            {
                "step": name,
                "seconds": time.monotonic() - started,
                "log": logfile.name,
                "command": command,
                "exit_code": child.returncode,
            }
        )
        status("RUNNING", f"Completed {name}")

    def json_file(path):
        return json.loads(Path(path).read_text())

    try:
        execute("unit-tests", "pytest", "tests", "-q")
        champion = ROOT / "champions" / "classical-v2"
        eligible = []
        for count, cap in [(100000, 256), (300000, 512)]:
            data = run / f"data-{count}"
            execute(
                f"collect-{count}",
                "training.dataset",
                "--positions",
                count,
                "--max-compressed-mb",
                cap,
                "--out",
                data,
            )
            dataset = data / "dataset.npz"
            trainings = []
            for hidden in [64, 128]:
                train = run / f"value-{count}-{hidden}"
                execute(
                    f"train-{count}-{hidden}",
                    "training.train",
                    "--data",
                    dataset,
                    "--out",
                    train,
                    "--hidden",
                    hidden,
                    "--epochs",
                    24,
                )
                metrics = json_file(train / "metrics.json")
                score = min(row["validation_mse"] for row in metrics["epochs"])
                trainings.append((score, train, hidden))
            _, best, hidden = min(trainings, key=lambda row: row[0])
            weights = run / f"value-{count}.npz"
            execute(
                f"export-{count}",
                "training.export",
                "--checkpoint",
                best / "best.npz",
                "--out",
                weights,
            )
            execute(
                f"evaluate-{count}",
                "training.evaluate_model",
                "--data",
                dataset,
                "--model",
                weights,
                "--out",
                run / f"evaluation-{count}.json",
            )
            for mode in ["neural", "hybrid"]:
                variant = run / f"candidate-{count}-{mode}"
                variant.mkdir()
                shutil.copy2(ROOT / "agent.py", variant / "agent.py")
                shutil.copytree(
                    ROOT / "engine",
                    variant / "engine",
                    ignore=shutil.ignore_patterns("__pycache__"),
                )
                (variant / "models").mkdir()
                shutil.copy2(weights, variant / "models" / "value.npz")
                (variant / "runtime.json").write_text(
                    json.dumps({"mode": mode, "style_tolerance": 0})
                )
                archive = run / f"candidate-{count}-{mode}.zip"
                execute(
                    f"package-{count}-{mode}",
                    "scripts.build_submission",
                    "--root",
                    variant,
                    "--out",
                    archive,
                )
                execute(
                    f"probe-{count}-{mode}",
                    "scripts.validate_package",
                    "--zip",
                    archive,
                    "--out",
                    run / f"probe-{count}-{mode}.json",
                )
                arena = run / f"arena-{count}-{mode}.json"
                execute(
                    f"screen-{count}-{mode}",
                    "scripts.arena_compare",
                    "--agent",
                    variant,
                    "--opponent",
                    champion,
                    "--games",
                    12,
                    "--out",
                    arena,
                )
                result = json_file(arena)
                if result["score"] < 0.55:
                    events.append(
                        {
                            "candidate": variant.name,
                            "decision": "rejected",
                            "score": result["score"],
                            "reason": "Failed quick strength screen",
                        }
                    )
                    continue
                arena_large = run / f"confirm-{count}-{mode}.json"
                execute(
                    f"confirm-{count}-{mode}",
                    "scripts.arena_compare",
                    "--agent",
                    variant,
                    "--opponent",
                    champion,
                    "--games",
                    64,
                    "--out",
                    arena_large,
                )
                confirm = json_file(arena_large)
                # Conservative bounded-score lower bound, pair as unit. Four candidates:
                # Bonferroni alpha=.05/4. Openings repeat, so still requires review.
                lower = confirm["score"] - math.sqrt(math.log(4 / 0.05) / (2 * 32))
                if lower <= 0.5:
                    events.append(
                        {
                            "candidate": variant.name,
                            "decision": "not_promoted",
                            "score": confirm["score"],
                            "lower_bound": lower,
                        }
                    )
                    continue
                execute(
                    f"real-clock-{count}-{mode}",
                    "scripts.arena_compare",
                    "--agent",
                    variant,
                    "--opponent",
                    champion,
                    "--games",
                    2,
                    "--base-ms",
                    120000,
                    "--increment-ms",
                    500,
                    "--ply-cap",
                    600,
                    "--out",
                    run / f"real-clock-{count}-{mode}.json",
                )
                eligible.append(
                    {
                        "candidate": str(variant),
                        "zip": str(archive),
                        "score": confirm["score"],
                        "lower_bound": lower,
                        "hidden": hidden,
                    }
                )
        (run / "eligible-candidates.json").write_text(json.dumps(eligible, indent=2))
        detail = f"Completed 100k/300k training and comparisons. {len(eligible)} candidate(s) passed the review gate. Classical submission preserved."
        status("COMPLETE", detail)
    except (TimeoutError, InterruptedError) as error:
        status(
            "STOPPED",
            str(error) + f"; last step: {current}. Completed outputs and checkpoints preserved.",
        )
    except Exception as error:
        status(
            "FAILED",
            f"{type(error).__name__}: {error}. Champion preserved; inspect the numbered log.",
        )
        raise


if __name__ == "__main__":
    main()
