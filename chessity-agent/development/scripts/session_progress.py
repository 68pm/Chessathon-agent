"""Read compact progress without holding Windows checkpoint files open."""

import json
import time
from pathlib import Path


def read_json(path):
    for attempt in range(10):
        try:
            return json.loads(path.read_text())
        except json.JSONDecodeError:
            if attempt == 9:
                raise
            time.sleep(0.025)


def main():
    root = Path("runs/witty-style-20260906")
    state = read_json(root / "session-status.json")
    download = json.loads(Path("data/witty_alien-history/download-status.json").read_text())
    report = {
        "session": state,
        "download": {
            "status": download["status"],
            "months": len(download.get("months", {})),
            "listed": download.get("archives_listed"),
            "games_in_months": sum(m["games"] for m in download.get("months", {}).values()),
            "unique_games": download.get("unique_games"),
            "parts": download.get("parts"),
        },
    }
    log = root / (state.get("stage", "history") + ".log")
    if log.exists():
        report["latest_log"] = log.read_text(encoding="utf-8", errors="replace").splitlines()[-3:]
    if (root / "rating.json").exists():
        rating = read_json(root / "rating.json")
        report["rating_games"] = len(rating.get("games", []))
        report["rating_status"] = rating["status"]
        report["rating_wdl"] = [
            sum(row["score"] == score for row in rating["games"]) for score in [1, 0.5, 0]
        ]
        if rating["status"] == "running" and (root / "rating.current.json").exists():
            current = read_json(root / "rating.current.json")
            report["current_game"] = {
                k: current[k] for k in ["elo", "candidate_white", "ply", "updated_utc"]
            }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
