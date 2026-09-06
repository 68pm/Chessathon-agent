"""Bounded CC0 puzzle importer, legal game branches and versioned verified pilot."""

import argparse
import csv
import hashlib
import io
import json
import random
import urllib.request
from collections import Counter, deque
from datetime import datetime, timezone
from pathlib import Path

import chess
import chess.pgn
import numpy as np
import zstandard

from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import SF
from training.dataset import BoundedReader
from training.puzzle_verifier import Verifier, duplicate_key

URL = "https://database.lichess.org/lichess_db_puzzle.csv.zst"
VERSION = "lichess-2026-08-02-puzzle-pilot-v1"
SEED = 20260909


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def family(themes):
    for key, tags in [
        ("mating_patterns", {"mate", "mateIn1", "mateIn2"}),
        ("defence", {"defensiveMove", "equality"}),
        ("endgame", {"endgame", "promotion", "underPromotion"}),
        ("combinations", {"sacrifice", "deflection", "interference", "attraction"}),
        ("quiet_ideas", {"quietMove", "zugzwang"}),
        ("punish_blunder", {"hangingPiece"}),
    ]:
        if set(themes) & tags:
            return key
    return "fundamental_tactics"


def decode_puzzle(raw):
    board = chess.Board(raw["FEN"])
    moves = raw["Moves"].split()
    if len(moves) < 2 or not board.is_valid():
        raise ValueError("Invalid source puzzle")
    original = board.fen()
    board.push_uci(moves[0])
    solver = board.fen()
    for uci in moves[1:]:
        board.push_uci(uci)
    themes = raw.get("Themes", "").split()
    game_id = raw["GameUrl"].split("lichess.org/")[-1].split("/")[0].split("#")[0]
    return {
        "id": "lichess:" + raw["PuzzleId"], "source_id": raw["PuzzleId"],
        "source_game_id": "lichess:" + game_id, "source_url": raw["GameUrl"],
        "dataset_version": VERSION, "family_id": "lichess:" + game_id,
        "origin_type": "lichess_cc0_puzzle", "original_record": raw,
        "original_fen": original, "setup_move_uci": moves[0], "solver_fen": solver,
        "solver_colour": "white" if chess.Board(solver).turn else "black",
        "relevant_history": {"start_fen": original, "moves": moves[:1], "complete": False},
        "draw_rule_context": "Prior repetitions unknown; no repetition-dependent objective; halfmove>=80 excluded.",
        "primary_family": family(themes), "secondary_themes": themes,
        "source_solution": moves[1:],
    }


def collect(out, scanned=2500):
    target = out / "lichess-prefix.jsonl"
    if target.exists():
        return [json.loads(s) for s in target.read_text().splitlines()]
    response = urllib.request.urlopen(URL, timeout=30)
    metadata = {"url": URL, "acquired_utc": datetime.now(timezone.utc).isoformat(),
                "licence": "CC0", "dataset_version": VERSION,
                "response_headers": {k: response.headers.get(k) for k in ["ETag", "Last-Modified", "Content-Length"]},
                "sampling": "First 2500 CSV records from bounded stream, then deterministic family-stratified ordering; not a random sample of the entire database."}
    raw = BoundedReader(response, 8_000_000)
    rows = []
    with response, zstandard.ZstdDecompressor().stream_reader(raw) as stream:
        reader = csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8"))
        required = {"PuzzleId", "FEN", "Moves", "GameUrl", "Themes"}
        if not required.issubset(reader.fieldnames):
            raise ValueError("Unexpected CSV header")
        metadata["header"] = reader.fieldnames
        for source in reader:
            rows.append(source)
            if len(rows) >= scanned:
                break
    target.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    metadata.update(records=len(rows), compressed_bytes_read=raw.bytes,
                    compressed_prefix_sha256=raw.hash.hexdigest(), subset_sha256=sha256(target))
    save_json(out / "acquisition.json", metadata)
    return rows


def game_branches():
    """Actual local games, plus legal alternatives. Whole game and all branches stay together."""
    result = json.loads(Path("runs/magnus-mixed-20260906/benchmark/results.json").read_text())
    rows = []
    games = sorted(result["games"], key=lambda r: digest(str(SEED) + r["pgn"]))[:24]
    for record in games:
        game = chess.pgn.read_game(io.StringIO(record["pgn"]))
        game_hash = digest(record["pgn"])
        board = game.board()
        history, possibilities = [], []
        for index, move in enumerate(game.mainline_moves()):
            if 15 <= index <= 100 and not board.is_game_over() and board.halfmove_clock < 70:
                possibilities.append((board.fen(), list(history), move.uci()))
            board.push(move)
            history.append(move.uci())
        possibilities.sort(key=lambda r: digest(str(SEED) + r[0]))
        for fen, prior, played in possibilities[:2]:
            ident = "local:" + game_hash + ":" + str(len(prior))
            row = dict(id=ident, source_id=ident, source_game_id="local:" + game_hash,
                       family_id="local:" + game_hash, dataset_version=VERSION,
                       source_url="local:docs/evidence/magnus-mixed-20260906-games.json",
                       origin_type="actual_local_game", original_fen=fen, solver_fen=fen,
                       setup_move_uci=None, played_uci=played,
                       solver_colour="white" if chess.Board(fen).turn else "black",
                       relevant_history={"start_fen": game.board().fen(), "moves": prior, "complete": True},
                       draw_rule_context="Full local game continuation retained; initial opening prefix is in game metadata.",
                       primary_family="ordinary_negative_control", secondary_themes=[])
            rows.append(row)
    return rows


def constructed():
    rng = random.Random(SEED)
    rows, seen = [], set()
    # Elementary KQK patterns. Board validity does not prove historical reachability.
    for _ in range(2000):
        board = chess.Board(None)
        squares = rng.sample(range(64), 3)
        for square, piece in zip(squares, [chess.Piece(chess.KING, True), chess.Piece(chess.QUEEN, True), chess.Piece(chess.KING, False)]):
            board.set_piece_at(square, piece)
        if not board.is_valid() or board.is_game_over():
            continue
        from training.puzzle_verifier import mate_moves
        accepted, _ = mate_moves(board)
        if not accepted or duplicate_key(board) in seen:
            continue
        seen.add(duplicate_key(board))
        if len(rows) % 2:
            board = board.mirror()
        ident = "constructed:" + digest(duplicate_key(board))
        rows.append(dict(id=ident, source_id=ident, source_game_id=ident,
                         family_id="constructed:kqk", dataset_version=VERSION,
                         origin_type="constructed_elementary", original_fen=board.fen(), solver_fen=board.fen(),
                         setup_move_uci=None, solver_colour="white" if board.turn else "black",
                         relevant_history={"complete": False, "moves": []},
                         draw_rule_context="Constructed board; reachability unproved; immediate mate only.",
                         primary_family="mating_patterns", secondary_themes=["mateIn1", "endgame"]))
        if len(rows) >= 12:
            break
    return rows


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--target", type=int, default=320)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    if (a.out / "manifest.json").exists():
        raise ValueError("Dataset already frozen")
    raw = collect(a.out)
    candidates, rejected = [], []
    for row in raw:
        try:
            candidates.append(decode_puzzle(row))
        except (ValueError, KeyError) as error:
            rejected.append({"id": row.get("PuzzleId"), "reason": str(error)})
    buckets = {}
    for row in candidates:
        buckets.setdefault(row["primary_family"], []).append(row)
    for group in buckets.values():
        group.sort(key=lambda r: digest(str(SEED) + r["id"]))
    candidates = [group[i] for i in range(max(map(len, buckets.values()))) for group in buckets.values() if i < len(group)]
    # Existing player rows and all original value positions are excluded from this new assessment pool.
    forbidden = set()
    for line in Path("runs/magnus-mixed-20260906/mixture/samples.jsonl").read_text().splitlines():
        forbidden.add(duplicate_key(chess.Board(json.loads(line)["fen"])))
    with np.load("runs/unattended-20260905-away/data-300000/dataset.npz", allow_pickle=False) as data:
        for fen in data["fen"]:
            forbidden.add(duplicate_key(chess.Board(str(fen))))
    print(f"Excluded {len(forbidden)} pre-existing canonical positions", flush=True)
    sources = deque(constructed() + game_branches() + candidates)
    verifier = Verifier(SF)
    accepted, seen = [], set()
    cache = a.out / "verification-cache.jsonl"
    cached = {r["id"]: r for r in [json.loads(s) for s in cache.read_text().splitlines()]} if cache.exists() else {}
    try:
        with cache.open("a", encoding="utf-8") as stream:
            while sources:
                candidate = sources.popleft()
                key = duplicate_key(chess.Board(candidate["solver_fen"]))
                if key in seen or key in forbidden:
                    continue
                seen.add(key)
                if candidate["id"] in cached:
                    record = cached[candidate["id"]]
                    verified, reason = record["verified"], record["reason"]
                else:
                    verified, reason = verifier.verify(candidate)
                    stream.write(json.dumps({"id": candidate["id"], "verified": verified, "reason": reason}) + "\n")
                    stream.flush()
                if verified:
                    accepted.append(verified)
                    # Linked alternatives from real play: select one confidently bad move and one sound move.
                    # Their objectives are independently reverified, never assumed tactic-free.
                    if candidate["origin_type"] == "actual_local_game" and verified["tempting_bad_moves_and_refutations"]:
                        for label, uci in [("mistake", verified["tempting_bad_moves_and_refutations"][0]["move"]), ("sound", verified["acceptable_first_moves"][0])]:
                            board = chess.Board(candidate["solver_fen"])
                            board.push_uci(uci)
                            branch = dict(candidate, id=candidate["id"] + ":" + label,
                                          origin_type="legal_branch_from_actual_game", solver_fen=board.fen(),
                                          setup_move_uci=uci, solver_colour="white" if board.turn else "black",
                                          primary_family="punish_blunder" if label == "mistake" else "ordinary_negative_control",
                                          linked_parent_id=candidate["id"], branch_role=label)
                            branch["relevant_history"] = {**candidate["relevant_history"], "moves": candidate["relevant_history"]["moves"] + [uci]}
                            sources.appendleft(branch)
                else:
                    rejected.append({"id": candidate["id"], "reason": reason})
                if len(accepted) % 20 == 0 and verified:
                    print(f"Accepted {len(accepted)}; quarantined {len(rejected)}", flush=True)
                if len(accepted) >= a.target:
                    break
    finally:
        verifier.close()
    # Keep constructed near-neighbours in a single TRAIN group, never an inflated held-out result.
    groups = {}
    for row in accepted:
        group = row["family_id"]
        code = int(digest(f"{SEED}:{group}")[:8], 16) % 100
        split = "train" if code < 80 or group.startswith("constructed:") else "validation" if code < 90 else "test"
        row["split"] = split
        groups.setdefault(group, set()).add(split)
    assert all(len(values) == 1 for values in groups.values())
    path = a.out / "verified.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in accepted), encoding="utf-8")
    save_json(a.out / "quarantine.json", rejected)
    save_json(a.out / "manifest.json", {
        "version": VERSION, "seed": SEED, "target": a.target, "accepted": len(accepted),
        "sha256": sha256(path), "teacher_sha256": sha256(SF),
        "splits": dict(Counter(r["split"] for r in accepted)),
        "families": dict(Counter(r["primary_family"] for r in accepted)),
        "origins": dict(Counter(r["origin_type"] for r in accepted)),
        "confidence": dict(Counter(r["confidence"] for r in accepted)),
        "colours": dict(Counter(r["solver_colour"] for r in accepted)),
        "excluded_prior_canonical_positions": len(forbidden), "source_game_split_overlap": 0,
        "verification_seconds": sum(r["verification_budget"]["seconds"] for r in accepted),
        "limitations": "Bounded source prefix and small pilot. Engine estimates are not exact proof. Related positions can remain; constructed neighbours kept train-only. Original value dataset lacks source game IDs, so cross-source game-level decontamination cannot be proved; exact/mirrored prior FENs excluded. No full repetition claim from incomplete history. No tablebase, RL, or 10000-position claim.",
    })
    print(json.dumps(json.loads((a.out / "manifest.json").read_text()), indent=2))


if __name__ == "__main__":
    main()
