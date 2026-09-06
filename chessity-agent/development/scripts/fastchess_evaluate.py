"""Held-out quality, low-clock reliability, equal-node judgement and separate opening recall."""

import os

for variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
    os.environ[variable] = "1"

import json
import subprocess
import sys
import time
from collections import Counter

import chess
import numpy as np

from engine.player_policy import PlayerPolicy
from harness.sandbox import local
from scripts.alien_rating_ladder import save_json, sha256
from scripts.fastchess_matches import CANDIDATE, CONTROL, STATIC
from scripts.magnus_benchmark import SF, manifest
from scripts.puzzle_evaluate import judge
from training.fastchess_data import (
    CONFIG,
    ROOT,
    RUN,
    clear_observation,
    enrich,
    prior_evidence,
    read_rows,
    restore,
    write_rows,
)
from training.puzzle_data import digest
from training.puzzle_verifier import Verifier, duplicate_key


def metrics(rows):
    groups = {}
    for label in sorted({(r["model"], r["mode"], r.get("clock_ms")) for r in rows}, key=str):
        group = [r for r in rows if (r["model"], r["mode"], r.get("clock_ms")) == label]
        cp = [r for r in group if r["assessment"].get("regret_cp") is not None]
        groups[":".join(map(str, label))] = dict(positions=len(group), accepted=sum(r["assessment"]["accepted"] for r in group),
            illegal=sum(not r["assessment"]["legal"] for r in group),
            measured_clock_overruns=sum(r.get("clock_ms") is not None and r["seconds"] * 1000 >= r["clock_ms"] for r in group),
            cp_positions=len(cp), blunders_200cp_both_budgets=sum(r["assessment"]["blunder"] for r in cp),
            mean_deep_regret_cp=float(np.mean([r["assessment"]["regret_cp"][1] for r in cp])) if cp else None,
            median_ms=float(np.median([r["seconds"] * 1000 for r in group])),
            p95_ms=float(np.percentile([r["seconds"] * 1000 for r in group], 95)),
            searched_nodes=sum(r.get("nodes", 0) for r in group),
            nodes_per_second=sum(r.get("nodes", 0) for r in group) / sum(r["seconds"] for r in group) if label[1] == "equal_nodes" else None,
            by_phase={phase: dict(positions=sum(r["phase"] == phase for r in group),
                                  accepted=sum(r["phase"] == phase and r["assessment"]["accepted"] for r in group))
                      for phase in sorted({r["phase"] for r in group})},
            by_task={task: dict(positions=sum(r.get("task") == task for r in group),
                                accepted=sum(r.get("task") == task and r["assessment"]["accepted"] for r in group))
                     for task in sorted({r.get("task", "board_decision") for r in group})})
    return groups


def opening_tasks(heldout, config, out):
    """Generate new history-linked continuations solely from untouched test games."""
    path = out / "opening-tasks.jsonl"
    if path.exists():
        return read_rows(path)
    anchors, counts = [], Counter()
    for row in sorted(heldout, key=lambda r: digest("opening-task" + r["id"])):
        family = row["opening_family"]
        if row["primary_phase"] in {"opening", "early_middlegame", "middlegame"} and counts[family] < 2:
            counts[family] += 1
            anchors.append(row)
    tasks, rejected, seen = [], [], set()
    # Depth claims use the actual stored graph, not an arbitrary six-ply extension.
    depth_coverage = {}
    graph_rows = read_rows(RUN / "data/opening-graph.jsonl")
    for family in config["graph_nodes"]:
        depth = max(len(r["relevant_history"]["moves"]) for r in graph_rows if r["opening_family"] == family)
        eligible = [r for r in heldout if r["opening_family"] == family
                    and len(r["relevant_history"]["moves"]) > depth]
        eligible.sort(key=lambda r: (len(r["relevant_history"]["moves"]), r["id"]))
        selected = eligible[0] if eligible else None
        depth_coverage[family] = dict(deepest_stored_ply=depth, eligible_test_positions=len(eligible),
            selected_id=selected["id"] if selected else None,
            selected_ply=len(selected["relevant_history"]["moves"]) if selected else None,
            scope="One already verified held-out game position beyond this family's deepest stored graph decision; not a full rollout or independent extra game.")
        if selected:
            tasks.append(dict(selected, task="after_deepest_stored_line"))
    save_json(out / "opening-depth-coverage.json", depth_coverage)
    # All original examples, including graph and training cases, are excluded from derived test boards.
    forbidden = {duplicate_key(chess.Board(r["solver_fen"])) for r in read_rows(RUN / "data/verified.jsonl")}
    old_keys, _, _ = prior_evidence()
    forbidden.update(old_keys)
    verifier = Verifier(SF, tuple(config["teacher_nodes"]))
    try:
        for anchor in anchors:
            tasks.append(dict(anchor, task="recall_unseen_board"))
            board = restore(anchor)
            deep = anchor["candidate_moves"][-1]
            best = anchor["recommended_move"]
            pv = deep[best]["pv"]
            variants = []
            if len(pv) >= 6:
                variants.append(("plan_unseen_continuation", pv[:6]))
            if len(pv) >= 2:
                variants.append(("sound_reply_control", pv[:2]))
            # A legal sideline is labelled afresh; it is not automatically a mistake.
            board.push_uci(best)
            replies = sorted(board.legal_moves, key=lambda m: digest(anchor["id"] + m.uci()))
            if replies:
                alternatives = [m.uci() for m in replies if len(pv) < 2 or m.uci() != pv[1]]
                if alternatives:
                    variants.append(("deviation", [best, alternatives[0]]))
            board.pop()
            bad = anchor["tempting_bad_moves_and_refutations"]
            if bad:
                variants.append(("refutation", [bad[0]["move"]]))
            for task, moves in variants:
                board = restore(anchor)
                for uci in moves:
                    board.push_uci(uci)
                key = duplicate_key(board)
                if key in forbidden or key in seen or board.is_game_over(claim_draw=True):
                    continue
                seen.add(key)
                candidate = dict(anchor, id=anchor["id"] + ":" + task, solver_fen=board.fen(),
                    played_uci=None, task=task, solver_colour="white" if board.turn else "black",
                    origin_type="heldout_legal_continuation", primary_family="punish_blunder" if task == "refutation" else "opening_decision",
                    relevant_history={**anchor["relevant_history"], "moves": anchor["relevant_history"]["moves"] + moves})
                clear_observation(candidate)
                verified, reason = verifier.verify(candidate)
                if verified:
                    tasks.append(enrich(verified))
                else:
                    rejected.append(dict(id=candidate["id"], reason=reason))
    finally:
        verifier.close()
    write_rows(path, tasks)
    save_json(out / "opening-task-rejections.json", rejected)
    return tasks


def main():
    out = RUN / "evaluation"
    if out.exists():
        raise ValueError("Fresh evaluation directory required")
    out.mkdir()
    config = json.loads(CONFIG.read_text())
    baseline = json.loads((ROOT / "runs/final-fusion-20260906/selection.json").read_text())
    assert baseline["status"] == "complete"
    models = dict(previous_best=ROOT / baseline["selected_path"], matched_control=CONTROL,
                  static_clock=STATIC, candidate=CANDIDATE)
    frozen = {name: manifest(path) for name, path in models.items()}
    all_rows = read_rows(RUN / "data/verified.jsonl")
    heldout = sorted([r for r in all_rows if r["split"] == "test"], key=lambda r: digest("assessment" + r["id"]))
    assert len(heldout) == config["human_verified_targets"]["test"]
    timed = heldout[:config["production_test_positions"]]
    node_tasks = heldout[:config["equal_node_positions"]]
    save_json(out / "node-tasks.json", node_tasks)
    related_tasks = opening_tasks(heldout, config, out)
    report = dict(status="running", config=config, data_sha256=sha256(RUN / "data/verified.jsonl"),
                  evaluation_source_files={str(path.relative_to(ROOT)): sha256(path)
                                           for path in sorted((ROOT / "scripts").glob("fastchess_*.py"))},
                  models=frozen, rows=[], graph_recall=[], overhead=[],
                  limits="Fresh whole-game split and canonical-board exclusion, with residual near-duplicate/old-value-game uncertainty. Root move estimates are not proof of full-game conversion. Opening graph recall is training-set recall, reported separately. Node caps use development-only tick instrumentation on each unchanged saved runtime.")
    for name, folder in models.items():
        policy_path = folder / "models/player-policy.npz"
        if policy_path.exists():
            policy = PlayerPolicy(policy_path)
            for row in heldout:
                board = chess.Board(row["solver_fen"])
                moves = list(board.legal_moves)
                tick = time.perf_counter()
                uci = moves[int(np.argmax(policy.logits(board, moves)))].uci()
                report["rows"].append(dict(model=name, mode="raw_policy", id=row["id"], phase=row["primary_phase"],
                    uci=uci, seconds=time.perf_counter() - tick, assessment=judge(row, uci), task="board_decision"))
            recall = []
            for row in read_rows(RUN / "data/opening-graph.jsonl"):
                board = chess.Board(row["solver_fen"])
                moves = list(board.legal_moves)
                uci = moves[int(np.argmax(policy.logits(board, moves)))].uci()
                recall.append(dict(id=row["id"], family=row["opening_family"], accepted=uci in row["acceptable_first_moves"]))
            report["graph_recall"].append(dict(model=name, positions=len(recall), accepted=sum(r["accepted"] for r in recall),
                                               rows=recall, label="Training-board recall; not evidence of held-out opening understanding"))
        # Fresh processes prevent unrelated test positions from sharing history or a transposition table.
        for row, clock, mode in [(row, clock, "production") for row in timed for clock in config["test_clocks_ms"]] + [(row, 4000, "opening_continuation") for row in related_tasks]:
            agent = local(folder)
            try:
                agent.start(90)
                tick = time.perf_counter()
                uci = agent.move(row["solver_fen"], clock)
                seconds = time.perf_counter() - tick
                report["rows"].append(dict(model=name, mode=mode, clock_ms=clock, id=row["id"],
                    phase=row["primary_phase"], task=row.get("task", "board_decision"), uci=uci,
                    seconds=seconds, assessment=judge(row, uci)))
            finally:
                agent.stop()
            save_json(out / "results.json", report)
        subprocess.run([sys.executable, "-B", "-m", "scripts.fastchess_node_probe", "--agent", str(folder),
                        "--tasks", str(out / "node-tasks.json"), "--nodes", str(config["equal_node_budget"]),
                        "--out", str(out / f"nodes-{name}.json")], cwd=ROOT, check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        lookup = {r["id"]: r for r in node_tasks}
        for result in json.loads((out / f"nodes-{name}.json").read_text()):
            row = lookup[result["id"]]
            report["rows"].append(dict(**result, model=name, mode="equal_nodes", phase=row["primary_phase"],
                                       task="board_decision", assessment=judge(row, result["uci"])))
        # Immediate legal fallback measures wire/scheduler overhead separately from search time.
        agent = local(folder)
        try:
            agent.start(90)
            samples = []
            for _ in range(20):
                tick = time.perf_counter()
                agent.move(chess.STARTING_FEN, 20)
                samples.append((time.perf_counter() - tick) * 1000)
            report["overhead"].append(dict(model=name, samples_ms=samples, p99_ms=float(np.percentile(samples, 99)),
                                           candidate_reserve_floor_ms=30, note="Includes fallback and protocol/scheduling; not pure IPC latency."))
        finally:
            agent.stop()
        report["summary"] = metrics(report["rows"])
        save_json(out / "results.json", report)
        print(f"Completed quality/clock/node assessment for {name}", flush=True)
    assert frozen == {name: manifest(path) for name, path in models.items()}
    subprocess.run([sys.executable, "-m", "scripts.fastchess_book_probe"], cwd=ROOT, check=True,
                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
    report["book_ablation"] = json.loads((out / "book-ablation.json").read_text())
    report["status"] = "complete"
    save_json(out / "results.json", report)


if __name__ == "__main__":
    main()
