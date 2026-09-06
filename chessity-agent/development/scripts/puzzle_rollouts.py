"""Short estimated-quality rollouts; horizon completion is not a solved chess game."""

import os

for variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
    os.environ[variable] = "1"

import argparse
import json
from pathlib import Path

import chess
import chess.engine
import numpy as np

from engine.player_policy import PlayerPolicy
from harness.sandbox import local
from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import SF
from scripts.puzzle_evaluate import judge
from training.puzzle_verifier import Verifier


def attempt(row, choose, verifier, horizon=3):
    solver = chess.Board(row["solver_fen"]).turn
    board = chess.Board(row["solver_fen"])
    original, history = board.fen(), []
    steps = []
    for turn in range(horizon):
        current = row if turn == 0 else dict(row, solver_fen=board.fen(),
                    relevant_history={"complete": True, "start_fen": original, "moves": history})
        if turn:
            current, reason = verifier.verify(current)
            if current is None:
                return dict(status="unresolved", reason=reason, steps=steps, truncated=True)
        uci = choose(board.fen())
        assessment = judge(current, uci)
        steps.append(dict(fen=board.fen(), student_uci=uci, assessment=assessment))
        if not assessment["legal"]:
            return dict(status="illegal", steps=steps, truncated=False)
        if not assessment["accepted"]:
            decisive = assessment.get("blunder") or assessment.get("missed_mate_objective")
            return dict(status="verified_quality_failure" if decisive else "uncertain_gap",
                        steps=steps, truncated=not decisive)
        board.push_uci(uci)
        history.append(uci)
        outcome = board.outcome(claim_draw=True)
        if outcome:
            return dict(status="game_draw" if outcome.winner is None else "game_win" if outcome.winner == solver else "game_loss", steps=steps, truncated=False)
        response = verifier.engine.play(board, chess.engine.Limit(nodes=320000), game=object())
        defence = response.move.uci()
        steps[-1]["defence_uci"] = defence
        board.push(response.move)
        history.append(defence)
        outcome = board.outcome(claim_draw=True)
        if outcome:
            return dict(status="game_draw" if outcome.winner is None else "game_win" if outcome.winner == solver else "game_loss", steps=steps, truncated=False)
    return dict(status="quality_horizon_passed", steps=steps, truncated=True,
                meaning="Three acceptable student decisions against analysed defence; game objective remains unresolved.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("Fresh rollout output required")
    rows = [json.loads(s) for s in (args.data / "verified.jsonl").read_text().splitlines()]
    by_family = {}
    for row in rows:
        if row["split"] == "test" and row["confidence"] == "engine_supported":
            by_family.setdefault(row["primary_family"], row)
    selected = [by_family[name] for name in sorted(by_family)][:8]
    models = {"baseline": "classical-witty-magnus-v1", "control": "puzzle-control-v1", "puzzle": "puzzle-mixed-v1"}
    report = {"selected_ids": [r["id"] for r in selected], "episodes": [],
              "selection": "First held-out engine-supported record per sorted family, at most eight; fixed without looking at student outcomes.",
              "teacher_sha256": sha256(SF), "student_clock_ms": 4000,
              "limits": "New positions are reverified at the original two budgets. Teacher chooses only opposing defences. Missing history before the supplied FEN remains unknown. Budget cutoff or short-horizon survival is not a solved puzzle, a draw, or a task reward. No RL rewards or repeat completion payments exist."}
    verifier = Verifier(SF)
    try:
        for name, candidate in models.items():
            folder = Path("candidates") / candidate
            policy = PlayerPolicy(folder / "models/player-policy.npz")

            def raw(fen):
                board = chess.Board(fen)
                moves = list(board.legal_moves)
                return moves[int(np.argmax(policy.logits(board, moves)))].uci()

            for row in selected:
                for mode in ["raw_policy", "production_agent"]:
                    agent = None
                    try:
                        if mode == "production_agent":
                            agent = local(folder)
                            agent.start(90)
                        choose = raw if agent is None else lambda fen: agent.move(fen, 4000)
                        episode = attempt(row, choose, verifier)
                        report["episodes"].append(dict(model=name, mode=mode, id=row["id"], **episode))
                        save_json(args.out, report)
                    finally:
                        if agent:
                            agent.stop()
            print(f"Completed {name} continuation rollout checks", flush=True)
    finally:
        verifier.close()
    report["status"] = "complete"
    save_json(args.out, report)


if __name__ == "__main__":
    main()
