"""Prepare move-imitation examples, not invented centipawn value labels."""

import hashlib
import heapq
import json
import random
from collections import Counter
from pathlib import Path

import chess
import chess.pgn

from training.style_analysis import alien_position


def prepare(
    pgn,
    output,
    player,
    max_positions=50000,
    per_game=20,
    seed=20260906,
    forcing_priority=True,
):
    if max_positions <= 0 or per_game <= 0:
        raise ValueError("Sample limits must be positive")
    seen_games, selected, heap = set(), {}, []
    counts = Counter()
    alien_key = alien_position()
    output = Path(output)
    temporary = output.with_name(output.name + ".tmp")
    output.parent.mkdir(parents=True, exist_ok=True)
    with Path(pgn).open(encoding="utf-8-sig", errors="replace") as stream:
        while (game := chess.pgn.read_game(stream)) is not None:
            counts["parsed_games"] += 1
            if counts["parsed_games"] % 5000 == 0:
                print(
                    f"Sampling full history: {counts['parsed_games']} games processed", flush=True
                )
            board = game.board()
            if game.errors or type(board) is not chess.Board or board.chess960:
                counts["invalid_or_variant_skipped"] += 1
                continue
            if game.headers.get("Result") not in {"1-0", "0-1", "1/2-1/2"}:
                counts["unfinished_skipped"] += 1
                continue
            colors = [
                color
                for color, field in [(chess.WHITE, "White"), (chess.BLACK, "Black")]
                if game.headers.get(field, "").lower() == player.lower()
            ]
            if len(colors) != 1:
                counts["unmatched_skipped"] += 1
                continue
            moves = list(game.mainline_moves())
            identity = game.headers.get("Link") or json.dumps(
                dict(game.headers), sort_keys=True
            ) + " ".join(m.uci() for m in moves)
            uid = hashlib.sha256(identity.encode()).hexdigest()
            if uid in seen_games:
                counts["duplicate_games_skipped"] += 1
                continue
            seen_games.add(uid)
            hashed = int(hashlib.sha256(f"{seed}:{uid}".encode()).hexdigest()[:8], 16)
            split = "train" if hashed % 100 < 80 else "validation" if hashed % 100 < 90 else "test"
            candidates = []
            for move in moves:
                if board.turn == colors[0]:
                    normalized = tuple(board.fen().split()[:4])
                    candidates.append(
                        {
                            "game_id": uid,
                            "split": split,
                            "fen": board.fen(),
                            "played_uci": move.uci(),
                            "gives_check": board.gives_check(move),
                            "is_capture": board.is_capture(move),
                            "alien_sacrifice": normalized == alien_key and move.uci() == "g5f7",
                            "game_result": game.headers["Result"],
                            "date": game.headers.get("Date", "unknown"),
                        }
                    )
                board.push(move)
            random.Random(hashed).shuffle(candidates)
            # Keep explicit Alien choices, then forcing moves, then sampled quiet moves.
            candidates.sort(
                key=lambda row: (
                    row["alien_sacrifice"],
                    forcing_priority and (row["gives_check"] or row["is_capture"]),
                ),
                reverse=True,
            )
            kept = 0
            for row in candidates:
                if kept >= per_game:
                    break
                fen_key = tuple(row["fen"].split()[:4])
                if fen_key in selected:
                    counts["duplicate_positions_skipped"] += 1
                    continue
                kept += 1
                counts["eligible_positions"] += 1
                # Bottom-k hash sampling spans the entire history, not its first months.
                # Priority depends on FEN so recurring openings do not gain extra tickets.
                priority = int(hashlib.sha256(f"{seed}:{fen_key}".encode()).hexdigest(), 16)
                if row["alien_sacrifice"]:
                    priority = -1
                if len(selected) >= max_positions and priority >= -heap[0][0]:
                    continue
                if len(selected) >= max_positions:
                    _, removed = heapq.heappop(heap)
                    del selected[removed]
                selected[fen_key] = row
                heapq.heappush(heap, (-priority, fen_key))
    with temporary.open("w", encoding="utf-8", newline="\n") as sink:
        for fen_key in sorted(selected):
            row = selected[fen_key]
            sink.write(json.dumps(row, separators=(",", ":")) + "\n")
            counts["positions"] += 1
            counts[row["split"]] += 1
            counts["alien_positions"] += int(row["alien_sacrifice"])
    temporary.replace(output)
    return {
        "counts": dict(counts),
        "seed": seed,
        "max_positions": max_positions,
        "per_game": per_game,
        "sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
        "schema": "FEN -> observed legal UCI move with whole-game split and factual move tags",
        "forcing_priority": forcing_priority,
        "sampling": "Whole-history deterministic bottom-k FEN hashes; shuffled decisions within each game, with an optional checks/captures priority. Exact FEN deduplication in the final sample. Alien sacrifice position reserved when present.",
        "limitations": "Move-imitation examples, not centipawn/value labels. No engine weights changed by preparation. Whole-game splits are fixed before sampling; no exact normalized FEN duplicates across splits. Related positions can remain across splits. Forcing-move prioritisation and first-occurrence deduplication bias the sample. Validate tactical quality and any trained candidate before deployment.",
    }
