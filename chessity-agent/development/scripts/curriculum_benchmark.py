"""Fixed, paired 32-game curriculum pilot; no automatic promotion."""

import concurrent.futures
import ctypes
import io
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import chess
import chess.pgn

from harness.referee import play_match
from harness.sandbox import local
from scripts import magnus_benchmark as backend
from scripts.alien_rating_ladder import save_json, sha256

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/carlsen-curriculum-20260906/benchmark"
CANDIDATE = ROOT / "candidates/carlsen-curriculum-v1"
OPPONENTS = {
    "control": ROOT / "candidates/carlsen-curriculum-control-v1",
    "baseline": ROOT / "candidates/classical-witty-magnus-v1",
}


def make_schedule(openings):
    result = []
    for family in ["control", "baseline"]:
        for pair, opening in enumerate(openings[:4]):
            for white in [True, False]:
                result.append(
                    dict(family=family, elo=None, pair=pair, white=white, opening=opening)
                )
    for family, elo in [
        ("madchess", 1500),
        ("madchess", 1700),
        ("madchess", 1900),
        ("stockfish", 1700),
    ]:
        for pair, opening in enumerate([openings[0], openings[5]]):
            for white in [True, False]:
                result.append(dict(family=family, elo=elo, pair=pair, white=white, opening=opening))
    return [{"id": i + 1, **job} for i, job in enumerate(result)]


def run_game(job):
    if job["family"] in {"madchess", "stockfish"}:
        return backend.run_game(job)
    if (ROOT / "STOP_BENCHMARK").exists():
        raise InterruptedError("STOP_BENCHMARK requested")
    start = time.perf_counter()
    board = chess.Board()
    for uci in job["opening"]:
        board.push_uci(uci)
    opponent = OPPONENTS[job["family"]]
    first, second = (CANDIDATE, opponent) if job["white"] else (opponent, CANDIDATE)
    outcome = play_match(
        local(first), local(second), 30000, 300, ply_cap=400, start_fen=board.fen()
    )
    score = (
        0.5
        if outcome.result == "draw"
        else float(outcome.result == ("white" if job["white"] else "black"))
    )
    game = chess.pgn.read_game(io.StringIO(outcome.pgn))
    game.headers.update(
        {
            "Event": "Carlsen curriculum fixed pilot",
            "Round": str(job["id"]),
            "White": first.name,
            "Black": second.name,
            "TimeControl": "30+0.3",
            "Termination": outcome.termination,
        }
    )
    row = {
        **job,
        "score": score,
        "termination": outcome.termination,
        "pgn": str(game),
        "seconds": time.perf_counter() - start,
    }
    save_json(RUN / f"game-{job['id']:03}.json", row)
    return row


def main():
    if RUN.exists():
        raise ValueError("Fresh curriculum benchmark required")
    RUN.mkdir()
    backend.CANDIDATE, backend.RUN = CANDIDATE, RUN
    logging.getLogger("chess.engine").setLevel(logging.ERROR)
    openings = json.loads((ROOT / "configs/mixed-benchmark-openings.json").read_text())
    jobs = make_schedule(openings)
    paths = {"candidate": CANDIDATE, **OPPONENTS}
    frozen = {name: backend.manifest(path) for name, path in paths.items()}
    report = {
        "status": "running",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "schedule": jobs,
        "files": frozen,
        "games": [],
        "base_ms": 30000,
        "increment_ms": 300,
        "workers": 2,
        "ply_cap": 400,
        "candidate_zip_sha256": sha256(CANDIDATE.with_suffix(".zip")),
        "protocol": json.loads((ROOT / "configs/carlsen-curriculum-pilot.json").read_text()),
        "engine_provenance": json.loads(
            (ROOT / "runs/magnus-mixed-20260906/benchmark/results.json").read_text()
        )["opponents"],
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
                report["summary"] = backend.summary(report["games"])
                save_json(RUN / "results.json", report)
                print(
                    f"{len(report['games'])}/32: {row['family']} {row['elo']} {row['score']} {row['termination']}",
                    flush=True,
                )
        assert frozen == {name: backend.manifest(path) for name, path in paths.items()}
        assert report["candidate_zip_sha256"] == sha256(CANDIDATE.with_suffix(".zip"))
        report["status"] = "complete"
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
