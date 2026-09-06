"""Describe factual position features and balance phases without rewarding a style."""

import argparse
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

import chess

from engine.evaluation import phase
from scripts.alien_rating_ladder import save_json, sha256

PHASES = ["opening", "early_middlegame", "middlegame", "transition", "endgame"]
PLAYERS = ["magnuscarlsen", "witty_alien"]


def describe(board, move):
    """Heuristic phase categories plus mechanically checked facts, not quality labels."""
    p = phase(board)
    back_rank_minors = sum(
        bool(board.pieces_mask(kind, color) & chess.BB_SQUARES[square])
        for color, squares in [(chess.WHITE, [1, 2, 5, 6]), (chess.BLACK, [57, 58, 61, 62])]
        for square in squares
        for kind in [chess.KNIGHT, chess.BISHOP]
    )
    queens = len(board.pieces(chess.QUEEN, True)) + len(board.pieces(chess.QUEEN, False))
    other_pieces = sum(len(board.pieces(k, c)) for c in chess.COLORS for k in [2, 3, 4])
    if p <= 0.25 or (p <= 0.42 and other_pieces <= 2):
        primary = "endgame"
    elif p <= 0.55 or queens < 2:
        primary = "transition"
    elif p >= 0.80 and back_rank_minors >= 3:
        primary = "opening"
    elif p >= 0.75 and back_rank_minors >= 1:
        primary = "early_middlegame"
    else:
        primary = "middlegame"
    tags = [primary]
    if primary == "transition" and p <= 0.42:
        tags.append("endgame")
    if primary == "early_middlegame":
        tags.append("middlegame")
    concepts = []
    if board.is_check():
        concepts.append("necessary_defence")
    if board.gives_check(move):
        concepts.append("played_check")
    if board.is_capture(move):
        concepts.append("played_capture")
    else:
        concepts.append("played_quiet_move")
    if board.is_castling(move):
        concepts.append("played_castling")
    if board.piece_type_at(move.from_square) == chess.KING:
        concepts.append("played_king_move")
    if move.promotion:
        concepts.append("played_promotion")
    if board.piece_type_at(move.to_square) == chess.QUEEN:
        concepts.append("captured_queen")
    pawns = board.pieces_mask(chess.PAWN, True) | board.pieces_mask(chess.PAWN, False)
    if any(not pawns & file_mask for file_mask in chess.BB_FILES):
        concepts.append("open_file_present")
    for color in chess.COLORS:
        enemies = board.pieces(chess.PAWN, not color)
        for pawn in board.pieces(chess.PAWN, color):
            if not any(
                abs(chess.square_file(enemy) - chess.square_file(pawn)) <= 1
                and (
                    chess.square_rank(enemy) > chess.square_rank(pawn)
                    if color
                    else chess.square_rank(enemy) < chess.square_rank(pawn)
                )
                for enemy in enemies
            ):
                concepts.append("passed_pawn_present")
                break
    return {
        "primary_phase": primary,
        "phase_tags": tags,
        "concept_tags": sorted(set(concepts)),
        "material_phase": p,
        "back_rank_minors": back_rank_minors,
        "queens": queens,
    }


def order(rows, seed):
    return sorted(
        rows, key=lambda r: hashlib.sha256(f"{seed}:{r['fen']}:{r['played_uci']}".encode()).digest()
    )


def choose(rows, count, balanced, seed):
    """Identical player shares; curriculum is half ordinary, half balanced by phase."""
    result = []
    for player in PLAYERS:
        pool = order([r for r in rows if r["player"] == player], seed)
        wanted = count // 2
        if len(pool) < wanted:
            raise ValueError("Insufficient unique source positions")
        selected = pool[: wanted if not balanced else wanted // 2]
        selected_keys = {r["fen"] for r in selected}
        if balanced:
            groups = {
                p: [r for r in pool if r["primary_phase"] == p and r["fen"] not in selected_keys]
                for p in PHASES
            }
            while len(selected) < wanted:
                progressed = False
                for p in PHASES:
                    if groups[p] and len(selected) < wanted:
                        selected.append(groups[p].pop())
                        progressed = True
                if not progressed:
                    raise ValueError("Insufficient phase sampling pool")
        result.extend(selected)
    return order(result, seed + 1)


def metadata(wanted):
    result = {}
    for player in PLAYERS:
        history = Path(f"data/{player}-history")
        status = json.loads((history / "download-status.json").read_text())
        for month in status["months"].values():
            path = history / month["file"]
            for record in json.loads(path.read_text())["games"]:
                pgn = record.get("pgn") or ""
                if not isinstance(pgn, str):
                    continue
                match = re.search(r'^\[Link "([^"\r\n]+)"\]', pgn, re.MULTILINE)
                if not match:
                    continue
                uid = hashlib.sha256(match.group(1).encode()).hexdigest()
                if uid not in wanted:
                    continue
                side = "white" if record["white"]["username"].lower() == player else "black"
                result[(player, uid)] = {
                    "source_url": match.group(1),
                    "source_month": str(path),
                    "source_pgn_sha256": hashlib.sha256(pgn.encode()).hexdigest(),
                    "player_side": side,
                    "time_control": record.get("time_control"),
                    "time_class": record.get("time_class", "unknown"),
                    "history_reference": "Full move history is recoverable from the source PGN; this policy takes FEN only and has no repetition-history features.",
                }
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument(
        "--samples", type=Path, default=Path("runs/magnus-mixed-20260906/mixture/samples.jsonl")
    )
    a = p.parse_args()
    if a.out.exists():
        raise ValueError("Fresh curriculum output required")
    a.out.mkdir(parents=True)
    rows = []
    for line in a.samples.read_text().splitlines():
        row = json.loads(line)
        if row["split"] == "test":
            continue  # No repeated inspection/selection on the previous final test set.
        board = chess.Board(row["fen"])
        move = chess.Move.from_uci(row["played_uci"])
        assert move in board.legal_moves
        rows.append(
            {
                **row,
                **describe(board, move),
                "label_kind": "observed_player_move_not_verified_optimum",
            }
        )
    train = [r for r in rows if r["split"] == "train"]
    validation = choose([r for r in rows if r["split"] == "validation"], 1024, True, 20260908)
    selected = {
        recipe: choose(train, 8192, recipe == "curriculum", 20260907) + validation
        for recipe in ["control", "curriculum"]
    }
    meta = metadata({r["game_id"] for group in selected.values() for r in group})
    report = {
        "source_sha256": sha256(a.samples),
        "seed": 20260907,
        "train_positions_per_recipe": 8192,
        "common_validation_positions": 1024,
        "test_positions_used": 0,
        "recipes": {},
        "phase_definition": "Heuristic remaining-material phase, queen count and minor pieces still on original back-rank squares. No fullmove-number boundary. Tags describe position features, never promise a sound move or plan.",
        "scope": "Data-only pilot: same 935-64-32-1 architecture, loss, initial checkpoint, 3 epochs, learning rate and search. Equal player shares. Curriculum mixes 50% ordinary sampling with 50% phase-balanced sampling. No automatic per-move rewards, teacher labels or speculative plan labels.",
        "endgame_runtime_limit": "Existing search bypasses player-policy bonuses at material phase <=0.20, in check, or with a large material/evaluation imbalance. This pilot trains endgame representations but does not enable them in those production positions.",
    }
    for recipe, group in selected.items():
        for row in group:
            row.update(meta[(row["player"], row["game_id"])])
            assert row["player_side"] == ("white" if chess.Board(row["fen"]).turn else "black")
        target = a.out / f"{recipe}.jsonl"
        target.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in group))
        report["recipes"][recipe] = {
            "sha256": sha256(target),
            "phases": dict(Counter(f"{r['split']}:{r['primary_phase']}" for r in group)),
            "concepts": dict(Counter(tag for r in group for tag in r["concept_tags"])),
            "time_classes": dict(Counter(r["time_class"] for r in group)),
            "split_games": {
                s: len({r["game_id"] for r in group if r["split"] == s})
                for s in ["train", "validation"]
            },
        }
    save_json(a.out / "manifest.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
