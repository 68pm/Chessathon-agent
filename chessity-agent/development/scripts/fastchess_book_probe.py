"""Known-position ablation of the existing optional Alien hint, separate from neural test accuracy."""

import json
import os
import subprocess
import sys
from collections import Counter

import chess

from engine.openings import ALIEN_FOLLOWUPS, ALIEN_LINE, alien_move
from scripts.alien_rating_ladder import save_json, sha256
from scripts.fastchess_matches import CANDIDATE
from scripts.magnus_benchmark import SF
from scripts.puzzle_evaluate import judge
from training.fastchess_data import CONFIG, ROOT, RUN, base_row
from training.puzzle_data import digest
from training.puzzle_verifier import Verifier, root_key


def main():
    out = RUN / "evaluation"
    config = json.loads(CONFIG.read_text())
    tasks, seen, rejected = [], set(), []
    verifier = Verifier(SF, tuple(config["teacher_nodes"]))
    try:
        for development in ["Nd2", "Nc3"]:
            for tail in [""] + ALIEN_FOLLOWUPS:
                line = ALIEN_LINE + tail.split()
                line[4] = development
                board, prefix = chess.Board(), []
                for san in line:
                    prepared = alien_move(board)
                    key = root_key(board)
                    if prepared and key not in seen:
                        seen.add(key)
                        row = base_row(board, "book-diagnostic:" + digest(key), "diagnostic", prefix,
                            family_id="known-handwritten-alien-line", primary_family="opening_decision",
                            origin_type="known_handwritten_opening", prepared_move=prepared.uci())
                        label, reason = verifier.verify(row)
                        if label:
                            tasks.append(label)
                        else:
                            rejected.append(dict(id=row["id"], reason=reason))
                    move = board.parse_san(san)
                    prefix.append(move.uci())
                    board.push(move)
    finally:
        verifier.close()
    save_json(out / "book-diagnostic-tasks.json", tasks)
    results = []
    lookup = {r["id"]: r for r in tasks}
    for mode in ["equal_nodes", "wall_clock"]:
        for enabled in [True, False]:
            destination = out / f"book-{mode}-{'on' if enabled else 'off'}.json"
            options = ["--clock-ms", "4000"] if mode == "wall_clock" else []
            if not enabled:
                options += ["--disable-opening"]
            subprocess.run([sys.executable, "-B", "-m", "scripts.fastchess_node_probe", "--agent", str(CANDIDATE),
                "--tasks", str(out / "book-diagnostic-tasks.json"), "--nodes", str(config["equal_node_budget"]),
                "--out", str(destination), *options], cwd=ROOT, check=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
            for row in json.loads(destination.read_text()):
                results.append(dict(**row, mode=mode, book_hint_enabled=enabled,
                                    follows_prepared_move=row["uci"] == lookup[row["id"]]["prepared_move"],
                                    assessment=judge(lookup[row["id"]], row["uci"])))
    summary = {}
    for mode in ["equal_nodes", "wall_clock"]:
        for enabled in [True, False]:
            rows = [r for r in results if r["mode"] == mode and r["book_hint_enabled"] == enabled]
            summary[f"{mode}:{'on' if enabled else 'off'}"] = dict(positions=len(rows),
                accepted=sum(r["assessment"]["accepted"] for r in rows),
                blunders=sum(r["assessment"].get("blunder") is True for r in rows),
                prepared_moves_followed=sum(r["follows_prepared_move"] for r in rows),
                total_seconds=sum(r["seconds"] for r in rows))
    save_json(out / "book-ablation.json", dict(status="complete", candidate_sha256=sha256(CANDIDATE.with_suffix(".zip")),
        tasks=len(tasks), rejected=rejected, rows=results, summary=summary,
        confidence=dict(Counter(r["confidence"] for r in tasks)),
        scope="The current permitted hand-written Alien preference is compared on/off at equal nodes and a 4,000ms remaining-clock input. Wall measurements call get_move directly, without wire overhead. These are known opening positions, not held-out neural accuracy or full-game strength evidence. The new teacher-verified graph remains offline and is not an inference book. No test or diagnostic label enters training."))
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    main()
