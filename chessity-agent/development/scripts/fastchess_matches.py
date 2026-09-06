"""Fresh 120+0.5 matches with both clocks, UCI increments and submission overhead recorded."""

import argparse
import concurrent.futures
import json
import logging
import os
import subprocess
import time
from collections import Counter
from datetime import datetime, timezone

import chess
import chess.engine
import chess.pgn
import numpy as np

from harness.sandbox import AgentFailure, local
from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import SF, manifest
from training.fastchess_data import CONFIG, ROOT, RUN

CANDIDATE = ROOT / "candidates/fastchess-adaptive-v1"
CONTROL = ROOT / "candidates/fastchess-control-v1"
STATIC = ROOT / "candidates/fastchess-static-v1"
FAILURES = {"flag", "illegal", "crash", "init", "both_failed"}


def host_cpu_sample():
    """Read host-wide counters without inspecting or changing other applications."""
    if os.name != "nt":
        return None
    import ctypes
    from ctypes.wintypes import FILETIME

    idle, kernel, user = FILETIME(), FILETIME(), FILETIME()
    if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
        return None
    def value(t):
        return (t.dwHighDateTime << 32) | t.dwLowDateTime

    return dict(idle=value(idle), total=value(kernel) + value(user))


def score_summary(rows):
    groups = {}
    for family in sorted({r["family"] for r in rows}):
        group = [r for r in rows if r["family"] == family]
        pairs = [sum(r["score"] for r in group if r["pair"] == p) / 2
                 for p in sorted({r["pair"] for r in group})
                 if sum(r["pair"] == p for r in group) == 2]
        rng = np.random.default_rng(20260910)
        interval = list(map(float, np.percentile(np.mean(rng.choice(pairs, (20000, len(pairs))), axis=1), [2.5, 97.5]))) if pairs else None
        groups[family] = dict(games=len(group), wins=sum(r["score"] == 1 for r in group),
            draws=sum(r["score"] == 0.5 for r in group), losses=sum(r["score"] == 0 for r in group),
            score=sum(r["score"] for r in group) / len(group), completed_pairs=len(pairs),
            pair_bootstrap_95=interval, terminations=dict(Counter(r["termination"] for r in group)),
            candidate_failures=sum(r.get("failed_colour") == ("white" if r["candidate_white"] else "black") for r in group))
    return groups


def run_game(job, config, out):
    if (ROOT / "STOP_BENCHMARK").exists():
        raise InterruptedError("STOP_BENCHMARK requested")
    candidate_path = ROOT / job["candidate_path"] if "candidate_path" in job else CANDIDATE
    board = chess.Board(job["start_fen"]) if "start_fen" in job else chess.Board()
    for uci in job["opening"]:
        board.push_uci(uci)
    # Curated starting positions carry no history before the game begins, identically for both colours.
    board = chess.Board(board.fen())
    game = chess.pgn.Game.from_board(board)
    node = game
    agents, opponent, clocks = {}, None, {True: float(config["base_ms"]), False: float(config["base_ms"])}
    candidate_colour = job["candidate_white"]
    moves, init, limit_records = [], {}, []
    termination, winner, failed_colour = "", None, None
    started = time.perf_counter()
    host_start = host_cpu_sample()
    try:
        for colour in [True, False]:
            tick = time.perf_counter()
            if colour == candidate_colour or "opponent_path" in job:
                folder = candidate_path if colour == candidate_colour else ROOT / job["opponent_path"]
                agents[colour] = local(folder)
                try:
                    agents[colour].start(90)
                except AgentFailure as error:
                    termination, winner, failed_colour = error.reason, not colour, "white" if colour else "black"
                    break
            else:
                opponent = chess.engine.SimpleEngine.popen_uci(str(SF.resolve()),
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
                opponent.configure({"UCI_LimitStrength": True, "UCI_Elo": job["elo"],
                                    "Threads": 1, "Hash": 64, "Move Overhead": 20})
            init["white" if colour else "black"] = (time.perf_counter() - tick) * 1000
        while not termination:
            outcome = board.outcome(claim_draw=True)
            if outcome:
                winner, termination = outcome.winner, outcome.termination.name.lower()
                break
            if board.ply() >= config["ply_cap"]:
                winner, termination = None, "ply_cap"
                break
            colour = board.turn
            before = clocks[colour]
            tick = time.perf_counter()
            try:
                if colour in agents:
                    answer = agents[colour].move(board.fen(), int(before))
                else:
                    limit = dict(white_clock=clocks[True] / 1000, black_clock=clocks[False] / 1000,
                                 white_inc=config["increment_ms"] / 1000, black_inc=config["increment_ms"] / 1000)
                    limit_records.append(dict(ply=board.ply(), **limit))
                    move = opponent.play(board, chess.engine.Limit(**limit), game=job["id"]).move
            except AgentFailure as error:
                termination = error.reason
                winner = None if termination == "flag" and board.has_insufficient_material(not colour) else not colour
                failed_colour = "white" if colour else "black"
                break
            elapsed = (time.perf_counter() - tick) * 1000
            clocks[colour] -= elapsed
            if clocks[colour] <= 0:
                termination = "flag"
                winner = None if board.has_insufficient_material(not colour) else not colour
                failed_colour = "white" if colour else "black"
                break
            if colour in agents:
                try:
                    move = chess.Move.from_uci(answer)
                except ValueError:
                    termination, winner, failed_colour = "illegal", not colour, "white" if colour else "black"
                    break
            if move not in board.legal_moves:
                termination, winner, failed_colour = "illegal", not colour, "white" if colour else "black"
                break
            san = board.san(move)
            fen = board.fen()
            board.push(move)
            clocks[colour] += config["increment_ms"]
            moves.append(dict(uci=move.uci(), san=san, fen=fen, white=colour,
                              clock_before_ms=before, elapsed_ms=elapsed, clock_after_ms=clocks[colour]))
            node = node.add_variation(move)
            node.set_clock(clocks[colour] / 1000)
            save_json(out / f"game-{job['id']:03}.current.json", dict(ply=board.ply(), fen=board.fen(),
                clocks_ms={"white": clocks[True], "black": clocks[False]}, updated_utc=datetime.now(timezone.utc).isoformat()))
    finally:
        for agent in agents.values():
            agent.stop()
        if opponent:
            opponent.quit()
    score = 0.5 if winner is None else float(winner == candidate_colour)
    opponent_name = job.get("opponent_path", f"Stockfish 19 UCI_Elo {job.get('elo')}")
    game.headers.update(Event="Chessity fast-chess verified pilot", Site="Local offline", TimeControl="120+0.5",
        White=candidate_path.name if candidate_colour else opponent_name,
        Black=opponent_name if candidate_colour else candidate_path.name,
        Result="1/2-1/2" if winner is None else "1-0" if winner else "0-1", Termination=termination,
        OpeningSetupUCI=" ".join(job["opening"]), Round=str(job["id"]))
    host_end = host_cpu_sample()
    total = host_end["total"] - host_start["total"] if host_start and host_end else 0
    busy = 1 - (host_end["idle"] - host_start["idle"]) / total if total > 0 else None
    row = dict(**job, score=score, termination=termination, failed_colour=failed_colour,
               host_cpu_busy_fraction=busy,
               host_load_scope="Host-wide average during game and initialization; includes all applications, not per-engine utilization or an isolated-core guarantee.",
               moves=moves, init_ms=init, uci_limits=limit_records, pgn=str(game),
               seconds=time.perf_counter() - started, final_fen=board.fen())
    save_json(out / f"game-{job['id']:03}.json", row)
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["comparison", "rated"], required=True)
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text())
    assert (config["base_ms"], config["increment_ms"], config["ply_cap"]) == (120000, 500, 600)
    baseline = json.loads((ROOT / "runs/final-fusion-20260906/selection.json").read_text())
    assert baseline["status"] == "complete"
    openings = json.loads((ROOT / "configs/fastchess-openings.json").read_text())
    jobs = []
    if args.stage == "comparison":
        paths = dict(previous_best=baseline["selected_path"], matched_control=CONTROL.relative_to(ROOT).as_posix(),
                     static_clock=STATIC.relative_to(ROOT).as_posix())
        for family, count in config["comparison_pairs"].items():
            for pair, opening in enumerate(openings[:count]):
                for white in [True, False]:
                    jobs.append(dict(family=family, pair=pair, opening=opening, candidate_white=white,
                                     opponent_path=paths[family]))
    else:
        for elo in config["rated_settings"]:
            for pair, opening in enumerate(openings[:config["rated_pairs_per_setting"]]):
                for white in [True, False]:
                    jobs.append(dict(family=f"stockfish:{elo}", elo=elo, pair=pair, opening=opening, candidate_white=white))
    jobs = [dict(id=i + 1, **job) for i, job in enumerate(jobs)]
    out = RUN / args.stage
    if out.exists():
        raise ValueError("Fresh match output required")
    out.mkdir()
    runtime_paths = {CANDIDATE, *[ROOT / job["opponent_path"] for job in jobs if "opponent_path" in job]}
    frozen = {path.relative_to(ROOT).as_posix(): manifest(path) for path in runtime_paths}
    report = dict(status="running", config=config, source_config_sha256=sha256(CONFIG), files=frozen,
                  match_source_sha256=sha256(__file__), host_logical_cpus=os.cpu_count(),
                  schedule=jobs, games=[], stockfish_sha256=sha256(SF),
                  scope="Paired-opening local pilot; score intervals resample whole colour pairs. Small samples and handicap settings cannot establish a human/site Elo.")
    assert report["stockfish_sha256"] == "45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0"
    logging.getLogger("chess.engine").setLevel(logging.ERROR)
    save_json(out / "results.json", report)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=config["workers"]) as pool:
            futures = [pool.submit(run_game, job, config, out) for job in jobs]
            for future in concurrent.futures.as_completed(futures):
                row = future.result()
                report["games"].append(row)
                report["games"].sort(key=lambda r: r["id"])
                report["summary"] = score_summary(report["games"])
                save_json(out / "results.json", report)
                print(f"{args.stage} {len(report['games'])}/{len(jobs)}: {row['family']} {row['score']} {row['termination']}", flush=True)
        assert frozen == {path.relative_to(ROOT).as_posix(): manifest(path) for path in runtime_paths}
        report["status"] = "complete"
    except BaseException as error:
        report.update(status="failed", error=repr(error))
        raise
    finally:
        save_json(out / "results.json", report)


if __name__ == "__main__":
    main()
