"""Frozen selection and fresh rated games at the actual 120+0.5 competition clock."""

import argparse
import concurrent.futures
import io
import json
import logging
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import chess
import chess.pgn

from harness.referee import play_match
from harness.sandbox import local
from scripts import magnus_benchmark as backend
from scripts.alien_rating_ladder import save_json, sha256

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/final-fusion-20260906"
AGENTS = {
    "classical": ROOT / "champions/classical-v2",
    "value-300k": ROOT / "runs/unattended-20260905-away/candidate-300000-hybrid",
    "magnus": ROOT / "candidates/classical-witty-magnus-v1",
    "puzzle": ROOT / "candidates/puzzle-mixed-v1",
    "fusion-hybrid": ROOT / "candidates/fusion-hybrid-v1",
    "fusion-root": ROOT / "candidates/fusion-root-v1",
}


def schedule(openings):
    names, jobs = list(AGENTS), []
    for i, first in enumerate(names):
        for j in range(i + 1, len(names)):
            second = names[j]
            opening = openings[(i + j) % len(openings)]
            for white, black in [(first, second), (second, first)]:
                jobs.append(dict(white=white, black=black, opening=opening, pair=f"{first}:{second}"))
    return [{"id": i + 1, **job} for i, job in enumerate(jobs)]


def comparison_game(job, config):
    if (ROOT / "STOP_BENCHMARK").exists():
        raise InterruptedError("STOP_BENCHMARK requested")
    board = chess.Board()
    for uci in job["opening"]:
        board.push_uci(uci)
    started = time.perf_counter()
    outcome = play_match(local(AGENTS[job["white"]]), local(AGENTS[job["black"]]),
                         config["base_ms"], config["increment_ms"], ply_cap=config["ply_cap"],
                         start_fen=board.fen())
    game = chess.pgn.read_game(io.StringIO(outcome.pgn))
    game.headers.update(Event="Chessity final fusion comparison", White=job["white"], Black=job["black"],
                        TimeControl="120+0.5", Termination=outcome.termination,
                        OpeningSetupUCI=" ".join(job["opening"]), Round=str(job["id"]))
    score = 0.5 if outcome.result == "draw" else 1.0 if outcome.result == "white" else 0.0
    row = dict(**job, white_score=score, termination=outcome.termination, pgn=str(game),
               seconds=time.perf_counter() - started)
    save_json(RUN / "comparison" / f"game-{job['id']:03}.json", row)
    if outcome.termination in {"illegal", "crash", "init", "both_failed"} or outcome.result == "void":
        raise RuntimeError(f"Reliability failure in {job['id']}: {outcome.termination}")
    return row


def standings(rows):
    scores = {name: Counter(games=0, points=0.0, wins=0, draws=0, losses=0) for name in AGENTS}
    for row in rows:
        for name, score in [(row["white"], row["white_score"]), (row["black"], 1 - row["white_score"])]:
            scores[name]["games"] += 1
            scores[name]["points"] += score
            scores[name][{1: "wins", 0.5: "draws", 0: "losses"}[score]] += 1
    return {name: dict(counts) for name, counts in scores.items()}


def rated_game(job):
    # backend clock variables are configured once, before any jobs start.
    row = backend.run_game(job)
    if row["termination"] == "invalid":
        raise RuntimeError(row)
    game = chess.pgn.read_game(io.StringIO(row["pgn"]))
    game.headers.update(Event="Chessity final 2000/2200 test", TimeControl="120+0.5")
    row["pgn"] = str(game)
    save_json(RUN / "rated" / f"game-{job['id']:03}.json", row)
    return row


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["comparison", "rated"], required=True)
    args = parser.parse_args()
    config = json.loads((ROOT / "configs/final-fusion.json").read_text())
    assert (config["base_ms"], config["increment_ms"], config["ply_cap"]) == (120000, 500, 600)
    openings = json.loads((ROOT / "configs/mixed-benchmark-openings.json").read_text())
    out = RUN / args.stage
    if out.exists():
        raise ValueError("Use fresh benchmark output; preserve completed results")
    out.mkdir()
    logging.getLogger("chess.engine").setLevel(logging.ERROR)
    report = {"status": "running", "config": config,
              "started_utc": datetime.now(timezone.utc).isoformat(), "games": []}
    if args.stage == "comparison":
        frozen = {name: backend.manifest(path) for name, path in AGENTS.items()}
        jobs = schedule(openings)
        def worker(job):
            return comparison_game(job, config)
        report["files"] = frozen
    else:
        selection = json.loads((RUN / "selection.json").read_text())
        backend.CANDIDATE = AGENTS[selection["selected_name"]]
        backend.RUN = out
        backend.BASE, backend.INC, backend.CAP = config["base_ms"], config["increment_ms"], config["ply_cap"]
        frozen = backend.manifest(backend.CANDIDATE)
        report["files"] = frozen
        report["selected_name"] = selection["selected_name"]
        report["stockfish_sha256"] = sha256(backend.SF)
        assert report["stockfish_sha256"] == "45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0"
        report["opponents"] = json.loads((ROOT / "runs/magnus-mixed-20260906/benchmark/results.json").read_text())["opponents"]
        jobs = []
        for elo in config["rated_settings"]:
            for pair, opening in enumerate(openings[:config["rated_pairs_per_setting"]]):
                for white in [True, False]:
                    jobs.append(dict(id=len(jobs) + 1, family="stockfish", elo=elo,
                                     pair=pair, white=white, opening=opening))
        worker = rated_game
    report["schedule"] = jobs
    save_json(out / "results.json", report)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=config["workers"]) as pool:
            futures = [pool.submit(worker, job) for job in jobs]
            for future in concurrent.futures.as_completed(futures):
                row = future.result()
                report["games"].append(row)
                report["games"].sort(key=lambda r: r["id"])
                report["summary"] = standings(report["games"]) if args.stage == "comparison" else backend.summary(report["games"])
                save_json(out / "results.json", report)
                print(f"{args.stage} {len(report['games'])}/{len(jobs)}: {row.get('white')} {row.get('black', row.get('elo'))} {row.get('white_score', row.get('score'))} {row['termination']}", flush=True)
        actual = {name: backend.manifest(path) for name, path in AGENTS.items()} if args.stage == "comparison" else backend.manifest(backend.CANDIDATE)
        assert frozen == actual
        report["status"] = "complete"
    except BaseException as error:
        report.update(status="failed", error=repr(error))
        raise
    finally:
        report["finished_utc"] = datetime.now(timezone.utc).isoformat()
        save_json(out / "results.json", report)
    if args.stage == "comparison":
        table = report["summary"]
        order = sorted(table, key=lambda name: (-table[name]["points"], config["tie_preference"].index(name)))
        chosen = order[0]
        save_json(RUN / "selection.json", {
            "status": "selected_pending_rated_tests", "selected_name": chosen,
            "selected_path": AGENTS[chosen].relative_to(ROOT).as_posix(),
            "selected_zip_sha256": sha256(AGENTS[chosen].with_suffix(".zip")),
            "standings": table, "ranking": order,
            "tie_preference": config["tie_preference"],
            "limitations": "Selection on a 30-game six-agent comparison (10 games per agent). Highest observed score is not proof of strongest possible play; exact ties use the predeclared order.",
        })


if __name__ == "__main__":
    main()
