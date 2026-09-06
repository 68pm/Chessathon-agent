"""Play a fixed, opening-conditioned ladder against MadChess's nominal Elo levels.

The external opponent stays outside the candidate and competition submission.
No weights are changed during this test and wins are never used as training labels.
"""

import argparse
import concurrent.futures
import ctypes
import hashlib
import io
import json
import logging
import os
import platform
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import chess
import chess.engine
import chess.pgn

from harness.sandbox import local


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def save_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    for attempt in range(20):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.05)


def history_opening(history):
    """Trace the actual retained Alien example back to its downloaded source PGN."""
    snapshot = history / json.loads((history / "latest.json").read_text())["export"]
    samples = snapshot / "style-samples.jsonl"
    with samples.open(encoding="utf-8") as stream:
        sample = next(json.loads(line) for line in stream if json.loads(line)["alien_sacrifice"])
    month = history / "months" / (sample["date"][:7].replace(".", "-") + ".json")
    for record in json.loads(month.read_text(encoding="utf-8"))["games"]:
        pgn = record.get("pgn")
        if not pgn:
            continue
        headers = chess.pgn.read_headers(io.StringIO(pgn))
        identity = headers.get("Link")
        if not identity or hashlib.sha256(identity.encode()).hexdigest() != sample["game_id"]:
            continue
        game = chess.pgn.read_game(io.StringIO(pgn))
        if game.errors or game.headers.get("White", "").lower() != "witty_alien":
            raise ValueError("Source is not a valid Witty_Alien White game")
        board, prefix = game.board(), []
        for move in game.mainline_moves():
            if board.fen() == sample["fen"] and move.uci() == "g5f7":
                return {
                    "source_url": identity,
                    "source_uuid": record.get("uuid"),
                    "source_pgn_sha256": hashlib.sha256(pgn.encode()).hexdigest(),
                    "source_month_sha256": sha256(month),
                    "source_date": sample["date"],
                    "sample_game_id": sample["game_id"],
                    "sample_split": sample["split"],
                    "samples_sha256": sha256(samples),
                    "opening_uci": prefix,
                    "start_fen": board.fen(),
                    "required_candidate_first_move": "g5f7",
                    "purpose": "Known repertoire position present in training, not a held-out position test. Only the first five full moves are supplied; all subsequent moves are played by the engines.",
                }
            prefix.append(move.uci())
            board.push(move)
    raise ValueError("Could not verify the Alien sample against an actual downloaded game")


def engine_options(engine, elos):
    option = engine.options.get("UCI_Elo")
    if not option or not engine.options.get("UCI_LimitStrength"):
        raise ValueError("Opponent does not advertise UCI Elo support")
    if any(not option.min <= elo <= option.max for elo in elos):
        raise ValueError(f"Requested Elo outside opponent range {option.min}..{option.max}")
    return {"Hash": 64, "UCI_LimitStrength": True}


def summarize(games, elos):
    rows = []
    for elo in elos:
        valid = [r for r in games if r["opponent_elo"] == elo and r.get("score") is not None]
        rows.append(
            {
                "opponent_elo": elo,
                "games": len(valid),
                "wins": sum(r["score"] == 1 for r in valid),
                "draws": sum(r["score"] == 0.5 for r in valid),
                "losses": sum(r["score"] == 0 for r in valid),
                "score": sum(r["score"] for r in valid),
            }
        )
    wins = [r for r in games if r.get("score") == 1 and r["termination"] == "checkmate"]
    return {
        "by_level": rows,
        "highest_nominal_level_defeated": max((r["opponent_elo"] for r in wins), default=None),
        "highest_level_with_majority_score": max(
            (r["opponent_elo"] for r in rows if r["games"] and r["score"] > r["games"] / 2),
            default=None,
        ),
        "wins": sum(r["wins"] for r in rows),
        "draws": sum(r["draws"] for r in rows),
        "losses": sum(r["losses"] for r in rows),
        "invalid_games": sum(r.get("score") is None for r in games),
    }


def play_game(agent, executable, opening, elo, repeat, base_ms, increment_ms, ply_cap, out):
    board = chess.Board()
    for move in opening["opening_uci"]:
        board.push_uci(move)
    assert board.fen() == opening["start_fen"]
    prefix_plies = len(board.move_stack)
    own, opponent = local(agent), None
    clocks = {chess.WHITE: float(base_ms), chess.BLACK: float(base_ms)}
    started = time.perf_counter()
    row = {"opponent_elo": elo, "repeat": repeat, "candidate_white": True, "score": None}
    moves = []
    try:
        own.start(90)
        opponent = chess.engine.SimpleEngine.popen_uci(
            str(executable),
            cwd=str(executable.parent),
            timeout=30,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        opponent.configure({**engine_options(opponent, [elo]), "UCI_Elo": elo})
        opponent.ping()
        while True:
            outcome = board.outcome(claim_draw=True)
            if outcome:
                row["score"] = 0.5 if outcome.winner is None else float(outcome.winner)
                row["termination"] = outcome.termination.name.lower()
                break
            if len(moves) >= ply_cap:
                row.update(score=0.5, termination="ply_cap")
                break
            save_json(
                out / f"level-{elo}-repeat-{repeat}.current.json",
                {
                    "elo": elo,
                    "repeat": repeat,
                    "played_plies": len(moves),
                    "fen": board.fen(),
                    "clocks_ms": {str(k): round(v, 2) for k, v in clocks.items()},
                    "updated_utc": datetime.now(timezone.utc).isoformat(),
                },
            )
            color, tick = board.turn, time.perf_counter()
            if color == chess.WHITE:
                move = chess.Move.from_uci(own.move(board.fen(), int(clocks[color])))
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
            elapsed = (time.perf_counter() - tick) * 1000
            clocks[color] -= elapsed
            if clocks[color] < 0:
                raise RuntimeError(f"{'Candidate' if color else 'Opponent'} exceeded clock")
            if move not in board.legal_moves:
                raise RuntimeError(f"Illegal move {move}")
            if not moves and move.uci() != opening["required_candidate_first_move"]:
                raise RuntimeError("Candidate did not choose the Alien Gambit sacrifice")
            moves.append(
                {
                    "uci": move.uci(),
                    "san": board.san(move),
                    "white": color,
                    "elapsed_ms": round(elapsed, 3),
                }
            )
            board.push(move)
            clocks[color] += increment_ms
    except Exception as error:
        row.update(score=None, termination="invalid", error=repr(error))
    finally:
        own.stop()
        if opponent:
            opponent.quit()
    game = chess.pgn.Game.from_board(board)
    game.headers.update(
        {
            "Event": "Witty-trained Alien Gambit fixed rating ladder",
            "Site": "Local offline benchmark",
            "Date": datetime.now().strftime("%Y.%m.%d"),
            "Round": f"{elo}.{repeat}",
            "White": agent.name,
            "Black": f"MadChess 3.4 x64 UCI_Elo {elo}",
            "BlackElo": str(elo),
            "TimeControl": f"{base_ms / 1000:g}+{increment_ms / 1000:g}",
            "Result": {1: "1-0", 0.5: "1/2-1/2", 0: "0-1", None: "*"}[row["score"]],
            "Termination": row["termination"],
            "Opening": "Caro-Kann: Alien Gambit",
            "OpeningSource": opening["source_url"],
            "OpeningSetupPlies": str(prefix_plies),
        }
    )
    node = game
    for _ in range(prefix_plies):
        node = node.next()
    node.comment = "Opening setup from downloaded Witty_Alien game ends here. Engine play starts with White's next move."
    row.update(
        moves=moves,
        played_plies=len(moves),
        pgn=str(game),
        seconds=round(time.perf_counter() - started, 3),
        alien_sacrifice_played=bool(moves and moves[0]["uci"] == "g5f7"),
        final_fen=board.fen(),
    )
    save_json(out / f"level-{elo}-repeat-{repeat}.json", row)
    return row


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--engine", type=Path, required=True)
    p.add_argument("--agent", type=Path, required=True)
    p.add_argument("--history", type=Path, default=Path("data/witty_alien-history"))
    p.add_argument("--elos", type=int, nargs="+", default=list(range(900, 2501, 100)))
    p.add_argument("--repeats", type=int, default=3)
    p.add_argument("--workers", type=int, choices=[1, 2], default=2)
    p.add_argument("--base-ms", type=int, default=30000)
    p.add_argument("--increment-ms", type=int, default=300)
    p.add_argument("--ply-cap", type=int, default=400)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError("Use a fresh output directory to preserve existing evidence")
    if a.repeats <= 0 or a.base_ms <= 0 or a.increment_ms < 0 or a.ply_cap < 2:
        raise ValueError("Invalid match limits")
    if len(a.elos) != len(set(a.elos)):
        raise ValueError("Duplicate ladder levels")
    a.engine, a.agent = a.engine.resolve(), a.agent.resolve()
    logging.getLogger("chess.engine").setLevel(logging.ERROR)  # MadChess emits blank UCI lines.
    with chess.engine.SimpleEngine.popen_uci(
        str(a.engine),
        cwd=str(a.engine.parent),
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
    ) as probe:
        if not probe.id.get("name", "").startswith("MadChess 3.4"):
            raise ValueError("This protocol records MadChess 3.4; select the matching release")
        options = engine_options(probe, a.elos)
        for elo in a.elos:
            probe.configure({**options, "UCI_Elo": elo})
            probe.ping()
        engine_id = probe.id
        elo_range = [probe.options["UCI_Elo"].min, probe.options["UCI_Elo"].max]
    opening = history_opening(a.history)
    a.out.mkdir(parents=True)
    manifest = {
        str(file.relative_to(a.agent)): sha256(file)
        for file in sorted(a.agent.rglob("*"))
        if file.is_file() and "__pycache__" not in file.parts and file.suffix != ".pyc"
    }
    report = {
        "status": "running",
        "started_utc": datetime.now(timezone.utc).isoformat(),
        "protocol": f"Fixed {a.repeats}-attempt-per-level Alien Gambit ladder; no adaptive stopping after wins/losses.",
        "engine_id": engine_id,
        "engine_sha256": sha256(a.engine),
        "engine_config_sha256": sha256(a.engine.parent / "MadChess.AdvancedConfig.json"),
        "engine_source": "https://www.madchess.net/wp-content/uploads/softwarereleases/MadChess-3-4.zip",
        "rating_documentation": "https://www.madchess.net/the-madchess-uci_limitstrength-algorithm/",
        "calibration_documentation": "https://www.madchess.net/the-madchess-uci_limitstrength-algorithm/limit-strength-faq/",
        "rating_caution": "Opponent numbers are MadChess's built-in nominal strength settings. Its author does not claim calibration to FIDE or a human pool. Highest single victory is not the candidate's Elo. Results are White-only from a prepared training position at the recorded time control, not general starting-position strength.",
        "candidate": a.agent.name,
        "candidate_manifest_sha256": manifest,
        "candidate_runtime": json.loads((a.agent / "runtime.json").read_text()),
        "opening": opening,
        "engine_options": options,
        "engine_elo_range": elo_range,
        "base_ms": a.base_ms,
        "increment_ms": a.increment_ms,
        "ply_cap": a.ply_cap,
        "elos": a.elos,
        "repeats_per_level": a.repeats,
        "concurrent_games": a.workers,
        "platform": platform.platform(),
        "randomness": "Opponent default internal randomization; no exposed seed option. Fresh processes each game. Both engines share this machine, at most two concurrent games.",
        "games": [],
    }
    save_json(a.out / "results.json", report)
    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        # A fixed schedule is submitted before any result is known.
        with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
            futures = [
                pool.submit(
                    play_game,
                    a.agent,
                    a.engine,
                    opening,
                    elo,
                    repeat,
                    a.base_ms,
                    a.increment_ms,
                    a.ply_cap,
                    a.out,
                )
                for elo in a.elos
                for repeat in range(1, a.repeats + 1)
            ]
            for future in concurrent.futures.as_completed(futures):
                row = future.result()
                report["games"].append(row)
                report["games"].sort(key=lambda r: (r["opponent_elo"], r["repeat"]))
                report["summary"] = summarize(report["games"], a.elos)
                report["updated_utc"] = datetime.now(timezone.utc).isoformat()
                save_json(a.out / "results.json", report)
                print(
                    f"{len(report['games'])}/{len(futures)}: {row['opponent_elo']} attempt {row['repeat']}: {row['score']} ({row['termination']}, {row['seconds']:.1f}s)",
                    flush=True,
                )
        assert all(sha256(a.agent / name) == digest for name, digest in manifest.items())
        report["status"] = "complete" if not report["summary"]["invalid_games"] else "failed"
    except Exception as error:
        report.update(status="failed", error=repr(error))
        raise
    finally:
        report["updated_utc"] = datetime.now(timezone.utc).isoformat()
        save_json(a.out / "results.json", report)
        (a.out / "games.pgn").write_text(
            "\n\n".join(r["pgn"] for r in report["games"]) + "\n", encoding="utf-8"
        )
        if os.name == "nt":
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
    print(json.dumps(report["summary"], indent=2), flush=True)


if __name__ == "__main__":
    main()
