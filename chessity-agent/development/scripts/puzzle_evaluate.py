"""Frozen held-out puzzle measurements: raw network and actual packaged agent."""

import os

for variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
    os.environ[variable] = "1"

import argparse
import json
import time
from collections import Counter
from pathlib import Path

import chess
import numpy as np

from engine.player_policy import PlayerPolicy
from harness.sandbox import local
from scripts.alien_rating_ladder import save_json, sha256
from scripts.curriculum_diagnostics import CASES, gold
from training.puzzle_verifier import duplicate_key


def judge(row, uci):
    board = chess.Board(row["solver_fen"])
    move = chess.Move.from_uci(uci)
    if move not in board.legal_moves:
        return {"legal": False, "accepted": False, "blunder": None}
    result = {"legal": True, "accepted": uci in row["acceptable_first_moves"],
              "objective": row["objective_type"], "confidence": row["confidence"]}
    if row["confidence"] == "exact":
        result.update(missed_mate_objective=not result["accepted"], blunder=None, regret_cp=None,
                      false_positive_attack=None)
    else:
        analyses = row["candidate_moves"]
        regrets = [max(v["cp"] for v in a.values()) - a[uci]["cp"] for a in analyses]
        blunder = min(regrets) >= 200
        negative = row["objective_type"] == "no_verified_tactical_win" or row["primary_family"] == "ordinary_negative_control"
        result.update(regret_cp=regrets, blunder=blunder,
                      uncertain_gap=not result["accepted"] and not blunder,
                      false_positive_attack=bool(negative and blunder and (board.is_capture(move) or board.gives_check(move))),
                      negative_control=negative)
    return result


def exact_continuation(row, first, choose, branch_cap=128):
    """Mate-objective success against every defence, including alternatives to the source PV."""
    board = chess.Board(row["solver_fen"])
    horizon = row["verification_budget"]["mate_horizon_plies"]
    if first not in row["acceptable_first_moves"]:
        return {"status": "failed", "branches_checked": 0, "cutoff": False}
    board.push_uci(first)
    if board.is_checkmate():
        return {"status": "success", "branches_checked": 1, "cutoff": False}
    if horizon != 3:
        return {"status": "unresolved", "branches_checked": 0, "cutoff": True}
    checked = 0
    for reply in list(board.legal_moves):
        if checked >= branch_cap:
            return {"status": "unresolved", "branches_checked": checked, "cutoff": True}
        board.push(reply)
        answer = choose(board.fen())
        if chess.Move.from_uci(answer) not in board.legal_moves:
            return {"status": "illegal", "branches_checked": checked, "cutoff": False}
        board.push_uci(answer)
        success = board.is_checkmate()
        board.pop()
        board.pop()
        checked += 1
        if not success:
            return {"status": "failed", "branches_checked": checked, "cutoff": False,
                    "defensive_reply": reply.uci(), "student_response": answer}
    return {"status": "success", "branches_checked": checked, "cutoff": False}


def summaries(rows):
    result = {}
    for name in sorted({r["model"] for r in rows}):
        for mode in ["raw_policy", "production_agent"]:
            group = [r for r in rows if r["model"] == name and r["mode"] == mode]
            estimated = [r for r in group if r["assessment"].get("regret_cp") is not None]
            exact = [r for r in group if r.get("continuation")]
            negative = [r for r in estimated if r["assessment"]["negative_control"]]
            accepted = sum(r["assessment"]["accepted"] for r in group)
            result[f"{name}:{mode}"] = {
                "positions": len(group), "accepted": accepted, "acceptance_rate": accepted / len(group),
                "illegal": sum(not r["assessment"]["legal"] for r in group),
                "cp_scored_positions": len(estimated),
                "blunders_200cp_both_budgets": sum(r["assessment"]["blunder"] for r in estimated),
                "mean_deep_regret_cp": float(np.mean([r["assessment"]["regret_cp"][1] for r in estimated])) if estimated else None,
                "negative_positions": len(negative), "false_positive_attacks": sum(r["assessment"]["false_positive_attack"] for r in negative),
                "exact_continuations": dict(Counter(r["continuation"]["status"] for r in exact)),
                "median_ms": float(np.median([r["seconds"] * 1000 for r in group])),
                "p95_ms": float(np.percentile([r["seconds"] * 1000 for r in group], 95)),
                "by_family": {family: {"positions": sum(r["family"] == family for r in group),
                                       "accepted": sum(r["family"] == family and r["assessment"]["accepted"] for r in group)}
                              for family in sorted({r["family"] for r in group})},
            }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--agent", action="append", required=True, help="name=folder")
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("Fresh evaluation path required")
    all_rows = [json.loads(s) for s in (args.data / "verified.jsonl").read_text().splitlines()]
    heldout = [r for r in all_rows if r["split"] == "test"]
    train = [r for r in all_rows if r["split"] == "train"]
    assert not {r["family_id"] for r in train} & {r["family_id"] for r in heldout}
    assert not {duplicate_key(chess.Board(r["solver_fen"])) for r in train} & {duplicate_key(chess.Board(r["solver_fen"])) for r in heldout}
    models = {s.split("=", 1)[0]: Path(s.split("=", 1)[1]) for s in args.agent}
    frozen = {name: sha256(path / "models/player-policy.npz") for name, path in models.items()}
    result = {"status": "running", "data_sha256": sha256(args.data / "verified.jsonl"),
              "models": frozen, "clock_ms_per_call": 4000, "rows": [], "diagnostics": [],
              "limits": "Untouched puzzle test, small group split. First-choice engine estimates are approximate. Full-objective continuation is proved only for exact short mates; longer material/positional/endgame tasks remain unmeasured. Known draw diagnostics are separate from held-out accuracy. Student moves use its own policy/search, never the teacher."}
    for name, folder in models.items():
        policy = PlayerPolicy(folder / "models/player-policy.npz")

        def raw_move(fen):
            board = chess.Board(fen)
            moves = list(board.legal_moves)
            return moves[int(np.argmax(policy.logits(board, moves)))].uci()

        for row in heldout:
            for mode in ["raw_policy", "production_agent"]:
                agent = None
                if mode == "production_agent":
                    agent = local(folder)
                    agent.start(90)
                choose = raw_move if agent is None else lambda fen: agent.move(fen, 4000)
                try:
                    start = time.perf_counter()
                    uci = choose(row["solver_fen"])
                    elapsed = time.perf_counter() - start
                    assessment = judge(row, uci)
                    continuation = exact_continuation(row, uci, choose) if row["confidence"] == "exact" else None
                    result["rows"].append(dict(model=name, mode=mode, id=row["id"], family=row["primary_family"],
                                               fen=row["solver_fen"], chosen_uci=uci, seconds=elapsed,
                                               assessment=assessment, continuation=continuation))
                finally:
                    if agent:
                        agent.stop()
            save_json(args.out, result)
        # Existing draw/promotion examples are known diagnostics, never counted as fresh test wins.
        for case, fen, kind in CASES:
            for mirrored in [False, True]:
                board = chess.Board(fen)
                if mirrored:
                    board = board.mirror()
                expected = gold(board, kind)
                if expected is None:
                    from engine.search import Search
                    outcome = Search(player_policy=policy, policy_cp=10).run(board, seconds=0.15)
                    passed = outcome.score == 0
                    uci = outcome.move.uci() if outcome.move else None
                else:
                    agent = local(folder)
                    try:
                        agent.start(90)
                        uci = agent.move(board.fen(), 4000)
                        passed = chess.Move.from_uci(uci) in expected
                    finally:
                        agent.stop()
                result["diagnostics"].append(dict(model=name, case=case, mirror=mirrored, passed=passed, uci=uci))
        print(f"Finished held-out evaluation for {name}: {len(heldout)} positions", flush=True)
    assert frozen == {name: sha256(path / "models/player-policy.npz") for name, path in models.items()}
    result.update(status="complete", summary=summaries(result["rows"]))
    save_json(args.out, result)
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
