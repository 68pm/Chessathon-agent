"""Offline matches against a user-supplied UCI engine; never included in submission.

The fitted rating is on this opponent's handicap scale, not a human/site rating.
"""

import argparse
import ctypes
import hashlib
import json
import math
import os
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import chess
import chess.engine
import chess.pgn
import numpy as np

from harness.sandbox import AgentFailure, local
from scripts.arena_compare import OPENINGS


def fit_rating(rows, fraction=None):
    """Fractional-score logistic fit, conditional on nominal opponent ratings."""
    total = sum(row["score"] for row in rows) if fraction is None else fraction * len(rows)
    if total == 0 or total == len(rows):
        return None
    low, high = -2000.0, 5000.0
    for _ in range(70):
        mid = (low + high) / 2
        expected = sum(1 / (1 + 10 ** ((r["opponent_elo"] - mid) / 400)) for r in rows)
        if expected < total:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def summarize(rows):
    result = {}
    for name in sorted({r["agent"] for r in rows}):
        games = [r for r in rows if r["agent"] == name]
        pairs = [[r for r in games if r["pair"] == k] for k in sorted({r["pair"] for r in games})]
        pairs = [p for p in pairs if len(p) == 2]
        complete = [r for pair in pairs for r in pair]
        if not complete:
            continue
        # Descriptive cluster bootstrap. Small samples and all-win/loss resamples
        # can produce unbounded endpoints; do not hide those by clipping.
        rng = np.random.default_rng(20260905)
        strata = [
            [p for p in pairs if p[0]["opponent_elo"] == elo]
            for elo in sorted({p[0]["opponent_elo"] for p in pairs})
        ]
        estimates = []
        for _ in range(3000):
            sampled = [
                r
                for group in strata
                for i in rng.integers(len(group), size=len(group))
                for r in group[i]
            ]
            rating = fit_rating(sampled)
            estimates.append(
                rating
                if rating is not None
                else (-math.inf if sum(r["score"] for r in sampled) == 0 else math.inf)
            )
        estimates.sort()
        lower, upper = estimates[75], estimates[2924]
        mean = sum(r["score"] for r in complete) / len(complete)
        # Avoid a falsely precise bootstrap when a small set of pairs looks alike.
        # Wilson's score band uses pair count as conservative effective sample size.
        # Its union with the bootstrap is descriptive, not an exact coverage claim.
        n, z = len(pairs), 1.96
        center = (mean + z * z / (2 * n)) / (1 + z * z / n)
        radius = z * math.sqrt(mean * (1 - mean) / n + z * z / (4 * n * n)) / (1 + z * z / n)
        wilson_low = fit_rating(complete, max(0, center - radius))
        wilson_high = fit_rating(complete, min(1, center + radius))
        envelope_low = min(lower, wilson_low if wilson_low is not None else -math.inf)
        envelope_high = max(upper, wilson_high if wilson_high is not None else math.inf)
        result[name] = {
            "games": len(complete),
            "wins": sum(r["score"] == 1 for r in complete),
            "draws": sum(r["score"] == 0.5 for r in complete),
            "losses": sum(r["score"] == 0 for r in complete),
            "score": mean,
            "nominal_handicap_scale_estimate": fit_rating(complete),
            "descriptive_pair_bootstrap_95": [
                lower if math.isfinite(lower) and n >= 4 else None,
                upper if math.isfinite(upper) and n >= 4 else None,
            ],
            "approximate_uncertainty_envelope": [
                envelope_low if math.isfinite(envelope_low) else None,
                envelope_high if math.isfinite(envelope_high) else None,
            ],
            "interval_method": "Union of nominal 95% colour-pair bootstrap stratified by opponent level and Wilson score interval with effective n=colour pairs, transformed through the fixed opponent-rating schedule. Descriptive small-sample approximation; no guaranteed coverage or calibration allowance.",
            "by_opponent": {
                str(elo): {
                    "games": len(group),
                    "score": sum(r["score"] for r in group) / len(group),
                }
                for elo in sorted({r["opponent_elo"] for r in complete})
                if (group := [r for r in complete if r["opponent_elo"] == elo])
            },
            "caution": "Nominal Stockfish handicap scale only. Small paired sample, fixed openings, one opponent family. Null interval endpoints are unbounded. Interval excludes calibration/hardware/time-control error; not FIDE, Chess.com, Lichess or official Chessathon Elo.",
        }
    return result


def play_game(
    agent_path, executable, elo, white, opening, base_ms, increment_ms, ply_cap, progress_path
):
    board = chess.Board()
    for uci in opening:
        board.push_uci(uci)
    # Match the official opening-FEN interface; prior book history is unavailable.
    board = chess.Board(board.fen())
    own = local(agent_path)
    opponent = None
    clocks = {chess.WHITE: float(base_ms), chess.BLACK: float(base_ms)}
    own_color = chess.WHITE if white else chess.BLACK
    termination, score = None, None
    started = time.perf_counter()
    try:
        own.start(90)
        opponent = chess.engine.SimpleEngine.popen_uci(
            str(executable),
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        opponent.configure(
            {
                "Threads": 1,
                "Hash": 64,
                "UCI_LimitStrength": True,
                "UCI_Elo": elo,
                "Move Overhead": 20,
            }
        )
        while True:
            outcome = board.outcome(claim_draw=True)
            if outcome:
                score = 0.5 if outcome.winner is None else float(outcome.winner == own_color)
                termination = outcome.termination.name.lower()
                break
            if len(board.move_stack) >= ply_cap:
                score, termination = 0.5, "ply_cap"
                break
            progress_path.write_text(
                json.dumps(
                    {
                        "agent": str(agent_path),
                        "elo": elo,
                        "candidate_white": white,
                        "ply": len(board.move_stack),
                        "fen": board.fen(),
                        "clocks_ms": {str(k): v for k, v in clocks.items()},
                        "updated_utc": datetime.now(timezone.utc).isoformat(),
                    },
                    indent=2,
                )
            )
            color = board.turn
            tick = time.perf_counter()
            if color == own_color:
                uci = own.move(board.fen(), int(clocks[color]))
                move = chess.Move.from_uci(uci)
            else:
                move = opponent.play(
                    board,
                    chess.engine.Limit(
                        white_clock=clocks[chess.WHITE] / 1000,
                        black_clock=clocks[chess.BLACK] / 1000,
                        white_inc=increment_ms / 1000,
                        black_inc=increment_ms / 1000,
                    ),
                    game=1,
                ).move
            clocks[color] -= (time.perf_counter() - tick) * 1000
            if clocks[color] < 0:
                score, termination = (float(color != own_color), "flag")
                break
            if move not in board.legal_moves:
                raise RuntimeError(f"Illegal move {move} from {color}")
            board.push(move)
            clocks[color] += increment_ms
    except AgentFailure as failure:
        raise RuntimeError(f"Agent failed: {failure.reason}") from failure
    finally:
        own.stop()
        if opponent:
            opponent.quit()
    game = chess.pgn.Game.from_board(board)
    game.headers["White"] = agent_path.name if white else f"Stockfish19_UCI_Elo_{elo}"
    game.headers["Black"] = f"Stockfish19_UCI_Elo_{elo}" if white else agent_path.name
    game.headers["TimeControl"] = f"{base_ms / 1000:g}+{increment_ms / 1000:g}"
    white_score = score if white else 1 - score
    game.headers["Result"] = {1: "1-0", 0.5: "1/2-1/2", 0: "0-1"}[white_score]
    game.headers["Termination"] = termination
    return {
        "score": score,
        "termination": termination,
        "plies": len(board.move_stack),
        "seconds": time.perf_counter() - started,
        "pgn": str(game),
        "candidate_white": white,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--engine", type=Path, required=True)
    p.add_argument("--agent", type=Path, action="append", required=True)
    p.add_argument("--elos", type=int, nargs="+", default=[1320, 1500, 1700])
    p.add_argument(
        "--pairs", type=int, default=6, help="Pairs per candidate, cycling the opponent levels"
    )
    p.add_argument("--base-ms", type=int, default=30000)
    p.add_argument("--increment-ms", type=int, default=300)
    p.add_argument("--ply-cap", type=int, default=400)
    p.add_argument("--openings", type=Path, help="JSON list of legal UCI opening sequences")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    openings = json.loads(a.openings.read_text()) if a.openings else OPENINGS
    if not isinstance(openings, list) or not openings:
        raise ValueError("Supply at least one opening sequence")
    for line in openings:
        board = chess.Board()
        for move in line:
            board.push_uci(move)
    if a.out.exists():
        raise ValueError("Use a fresh output file to preserve benchmark evidence")
    a.out.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "status": "running",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "engine": str(a.engine.resolve()),
        "engine_sha256": hashlib.sha256(a.engine.read_bytes()).hexdigest(),
        "source": "https://github.com/official-stockfish/Stockfish/releases/tag/sf_19",
        "platform": platform.platform(),
        "base_ms": a.base_ms,
        "increment_ms": a.increment_ms,
        "elos": a.elos,
        "pairs_per_agent": a.pairs,
        "opening_schedule": openings,
        "games": [],
        "calibration_caution": "SF19 documentation says 120+1 calibration, CCRL40/4 anchor. Other clocks change strength. No direct human/site rating conversion.",
    }
    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        for pair in range(a.pairs):
            for candidate in a.agent:
                for white in [True, False]:
                    if Path("STOP_BENCHMARK").exists():
                        report["status"] = "stopped"
                        return
                    elo = a.elos[pair % len(a.elos)]
                    row = play_game(
                        candidate,
                        a.engine,
                        elo,
                        white,
                        openings[pair % len(openings)],
                        a.base_ms,
                        a.increment_ms,
                        a.ply_cap,
                        a.out.with_suffix(".current.json"),
                    )
                    row.update({"agent": candidate.name, "pair": pair, "opponent_elo": elo})
                    report["games"].append(row)
                    a.out.write_text(json.dumps(report, indent=2))
                    print(
                        f"Game {len(report['games'])}: {candidate.name} vs {elo} {'White' if white else 'Black'}: {row['score']} ({row['termination']}, {row['seconds']:.1f}s)",
                        flush=True,
                    )
                    if row["termination"] == "flag":
                        raise RuntimeError("Time failure: benchmark stopped for inspection")
        report["status"] = "complete"
    except Exception as error:
        report["status"], report["error"] = "failed", repr(error)
        raise
    finally:
        report["summary"] = summarize(report["games"])
        report["updated_utc"] = datetime.now(timezone.utc).isoformat()
        a.out.write_text(json.dumps(report, indent=2))
        print(json.dumps(report["summary"], indent=2), flush=True)
        if os.name == "nt":
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == "__main__":
    main()
