"""A fixed 92-game test of the frozen Magnus/Witty/classical candidate."""

import concurrent.futures
import ctypes
import io
import json
import logging
import os
import platform
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import chess
import chess.engine
import chess.pgn

from harness.referee import play_match
from harness.sandbox import local
from scripts.alien_rating_ladder import engine_options, save_json, sha256

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/magnus-mixed-20260906/benchmark"
CANDIDATE = ROOT / "candidates/classical-witty-magnus-v1"
PREVIOUS = ROOT / "candidates/mixed-classical-witty-v1"
MAD = ROOT / "../../work/benchmark-tools/madchess-3.4/release/MadChess/x64/MadChess.Engine.exe"
SF = (
    ROOT
    / "../../work/benchmark-tools/stockfish-19/stockfish/stockfish-windows-x86-64-universal.exe"
)
BASE, INC, CAP = 30000, 300, 400


def schedule(openings):
    jobs = []
    for elo in range(900, 2501, 100):
        for pair, opening in enumerate([openings[0], openings[5]]):
            for white in [True, False]:
                jobs.append(
                    dict(family="madchess", elo=elo, pair=pair, white=white, opening=opening)
                )
    for family in ["stockfish", "previous"]:
        for pair, opening in enumerate(openings):
            for white in [True, False]:
                jobs.append(
                    dict(
                        family=family,
                        elo=1700 if family == "stockfish" else None,
                        pair=pair,
                        white=white,
                        opening=opening,
                    )
                )
    return [{"id": i + 1, **job} for i, job in enumerate(jobs)]


def manifest(path):
    return {
        f.relative_to(path).as_posix(): sha256(f)
        for f in sorted(path.rglob("*"))
        if f.is_file() and "__pycache__" not in f.parts and f.suffix != ".pyc"
    }


def summary(rows):
    groups = {}
    for row in rows:
        key = f"{row['family']}:{row['elo']}"
        group = groups.setdefault(key, Counter())
        group["games"] += 1
        group[{1: "wins", 0.5: "draws", 0: "losses", None: "invalid"}[row["score"]]] += 1
        if row["termination"] in {"flag", "ply_cap", "invalid"}:
            group[row["termination"] + "_terminations"] += 1
    return {
        "by_opponent": {key: dict(value) for key, value in groups.items()},
        "highest_checkmate_win_by_family": {
            family: max(
                (
                    r["elo"]
                    for r in rows
                    if r["family"] == family and r["score"] == 1 and r["termination"] == "checkmate"
                ),
                default=None,
            )
            for family in ["madchess", "stockfish"]
        },
        "terminations": dict(Counter(row["termination"] for row in rows)),
    }


def play_uci(job, board):
    executable = (MAD if job["family"] == "madchess" else SF).resolve()
    own, opponent = local(CANDIDATE), None
    clocks = {True: float(BASE), False: float(BASE)}
    moves = []
    score, termination = None, "invalid"
    try:
        own.start(90)
        opponent = chess.engine.SimpleEngine.popen_uci(
            str(executable),
            cwd=str(executable.parent),
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        options = {**engine_options(opponent, [job["elo"]]), "UCI_Elo": job["elo"]}
        if job["family"] == "stockfish":
            options.update({"Threads": 1, "Move Overhead": 20})
        opponent.configure(options)
        opponent.ping()
        while True:
            outcome = board.outcome(claim_draw=True)
            if outcome:
                score = 0.5 if outcome.winner is None else float(outcome.winner == job["white"])
                termination = outcome.termination.name.lower()
                break
            if len(moves) >= CAP:
                score, termination = 0.5, "ply_cap"
                break
            save_json(
                RUN / f"game-{job['id']:03}.current.json",
                {
                    **job,
                    "played_plies": len(moves),
                    "fen": board.fen(),
                    "clocks_ms": {str(k): round(v, 2) for k, v in clocks.items()},
                    "updated_utc": datetime.now(timezone.utc).isoformat(),
                },
            )
            color, tick = board.turn, time.perf_counter()
            if color == job["white"]:
                move = chess.Move.from_uci(own.move(board.fen(), int(clocks[color])))
            else:
                move = opponent.play(
                    board,
                    chess.engine.Limit(
                        white_clock=clocks[True] / 1000,
                        black_clock=clocks[False] / 1000,
                        white_inc=INC / 1000,
                        black_inc=INC / 1000,
                    ),
                    game=job["id"],
                ).move
            elapsed = (time.perf_counter() - tick) * 1000
            clocks[color] -= elapsed
            if clocks[color] < 0:
                score, termination = float(color != job["white"]), "flag"
                break
            if move not in board.legal_moves:
                raise ValueError(f"Illegal move {move}")
            moves.append(
                {
                    "uci": move.uci(),
                    "san": board.san(move),
                    "white": color,
                    "elapsed_ms": round(elapsed, 3),
                }
            )
            board.push(move)
            clocks[color] += INC
    finally:
        own.stop()
        if opponent:
            opponent.quit()
    game = chess.pgn.Game.from_board(board)
    return dict(
        score=score, termination=termination, moves=moves, pgn=str(game), final_fen=board.fen()
    )


def run_game(job):
    if (ROOT / "STOP_BENCHMARK").exists():
        raise InterruptedError("STOP_BENCHMARK requested")
    tick = time.perf_counter()
    board = chess.Board()
    for uci in job["opening"]:
        board.push_uci(uci)
    board = chess.Board(board.fen())
    try:
        if job["family"] == "previous":
            first, second = (CANDIDATE, PREVIOUS) if job["white"] else (PREVIOUS, CANDIDATE)
            outcome = play_match(
                local(first), local(second), BASE, INC, ply_cap=CAP, start_fen=board.fen()
            )
            score = (
                0.5
                if outcome.result == "draw"
                else float(outcome.result == ("white" if job["white"] else "black"))
            )
            result = dict(score=score, termination=outcome.termination, pgn=outcome.pgn)
        else:
            result = play_uci(job, board)
        result.update(job)
        game = chess.pgn.read_game(io.StringIO(result["pgn"]))
        opponent_name = (
            PREVIOUS.name
            if job["family"] == "previous"
            else f"{job['family']} UCI_Elo {job['elo']}"
        )
        white_score = result["score"] if job["white"] else 1 - result["score"]
        game.headers.update(
            {
                "Event": "Classical Witty Magnus fixed benchmark",
                "Site": "Local offline",
                "Date": datetime.now().strftime("%Y.%m.%d"),
                "Round": str(job["id"]),
                "White": CANDIDATE.name if job["white"] else opponent_name,
                "Black": opponent_name if job["white"] else CANDIDATE.name,
                "Result": {1: "1-0", 0.5: "1/2-1/2", 0: "0-1"}[white_score],
                "Termination": result["termination"],
                "TimeControl": "30+0.3",
                "OpeningSetupUCI": " ".join(job["opening"]),
            }
        )
        result["pgn"] = str(game)
    except Exception as error:
        result = {**job, "score": None, "termination": "invalid", "error": repr(error)}
    result["seconds"] = round(time.perf_counter() - tick, 3)
    save_json(RUN / f"game-{job['id']:03}.json", result)
    return result


def main():
    import argparse

    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--probe-only", action="store_true")
    a = p.parse_args()
    logging.getLogger("chess.engine").setLevel(logging.ERROR)
    openings = json.loads((ROOT / "configs/mixed-benchmark-openings.json").read_text())
    jobs, probes = schedule(openings), {}
    for family, executable, levels in [
        ("madchess", MAD, range(900, 2501, 100)),
        ("stockfish", SF, [1700]),
    ]:
        executable = executable.resolve()
        with chess.engine.SimpleEngine.popen_uci(
            str(executable),
            cwd=str(executable.parent),
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        ) as engine:
            if (
                not engine.id["name"]
                .lower()
                .startswith("madchess 3.4" if family == "madchess" else "stockfish 19")
            ):
                raise ValueError("Unexpected engine release")
            options = engine_options(engine, levels)
            if family == "stockfish":
                options.update({"Threads": 1, "Move Overhead": 20})
            for elo in levels:
                engine.configure({**options, "UCI_Elo": elo})
                engine.ping()
            probes[family] = {
                "id": engine.id,
                "options": options,
                "tested_levels": list(levels),
                "sha256": sha256(executable),
                "path": str(executable),
            }
    probes["madchess"]["advanced_config_sha256"] = sha256(
        MAD.parent / "MadChess.AdvancedConfig.json"
    )
    if a.probe_only:
        print(json.dumps(probes, indent=2))
        return
    training = json.loads((ROOT / "runs/magnus-mixed-20260906/training-session.json").read_text())
    if training["status"] != "complete":
        raise ValueError("Training and package validation must finish first")
    if RUN.exists() or (ROOT / "STOP_BENCHMARK").exists():
        raise ValueError("Existing benchmark or stop marker; inspect before rerunning")
    RUN.mkdir()
    report = {
        "status": "running",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "candidate_files": manifest(CANDIDATE),
        "previous_files": manifest(PREVIOUS),
        "candidate_zip_sha256": sha256(CANDIDATE.with_suffix(".zip")),
        "opponents": probes,
        "schedule": jobs,
        "base_ms": BASE,
        "increment_ms": INC,
        "ply_cap": CAP,
        "workers": 2,
        "platform": platform.platform(),
        "games": [],
        "protocol": "Fixed before outcomes: four games per MadChess level, two colours from the start and a Caro-Kann prefix; twelve each against SF1700 and the previous candidate from six colour-paired openings. No opening move forced after setup, no model changes, no adaptive retests.",
        "caution": "Nominal opponent difficulty settings, not official human or competition Elo. Highest single victory is not a rating. Small samples; shared hardware, fresh opponent processes and default opponent randomness.",
    }
    save_json(RUN / "results.json", report)
    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run_game, job) for job in jobs]
            for future in concurrent.futures.as_completed(futures):
                row = future.result()
                report["games"].append(row)
                report["games"].sort(key=lambda r: r["id"])
                report["summary"] = summary(report["games"])
                report["updated_utc"] = datetime.now(timezone.utc).isoformat()
                save_json(RUN / "results.json", report)
                print(
                    f"{len(report['games'])}/92: {row['family']} {row['elo']} {row['score']} {row['termination']}",
                    flush=True,
                )
        assert manifest(CANDIDATE) == report["candidate_files"]
        assert manifest(PREVIOUS) == report["previous_files"]
        assert sha256(CANDIDATE.with_suffix(".zip")) == report["candidate_zip_sha256"]
        report["status"] = (
            "complete"
            if all(
                r["termination"] not in {"invalid", "crash", "illegal", "init", "both_failed"}
                for r in report["games"]
            )
            else "failed"
        )
    except BaseException as error:
        report.update(status="failed", error=repr(error))
        raise
    finally:
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        save_json(RUN / "results.json", report)
        if os.name == "nt":
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == "__main__":
    main()
