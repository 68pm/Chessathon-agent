"""Aggregate chess decisions from locally supplied, permitted PGNs; no network access."""

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

import chess
import chess.pgn

from engine.openings import ALIEN_LINE, key


def alien_position():
    b = chess.Board()
    for san in ALIEN_LINE[:10]:
        b.push_san(san)
    return key(b)


def analyze(paths, player):
    totals, openings, classes = Counter(), Counter(), defaultdict(Counter)
    seen = set()
    alien_key = alien_position()
    for path in paths:
        with path.open(encoding="utf-8-sig", errors="replace") as stream:
            while (game := chess.pgn.read_game(stream)) is not None:
                totals["parsed_games"] += 1
                if totals["parsed_games"] % 5000 == 0:
                    print(
                        f"Analysing player history: {totals['parsed_games']} games processed",
                        flush=True,
                    )
                if game.errors:
                    totals["invalid_games_skipped"] += 1
                    continue
                board = game.board()
                if type(board) is not chess.Board or board.chess960:
                    totals["variant_games_skipped"] += 1
                    continue
                colors = [
                    color
                    for color, header in [(chess.WHITE, "White"), (chess.BLACK, "Black")]
                    if game.headers.get(header, "").lower() == player.lower()
                ]
                if len(colors) != 1:
                    totals["unmatched_games_skipped"] += 1
                    continue
                moves = list(game.mainline_moves())
                identity = game.headers.get("Link") or (
                    json.dumps(dict(game.headers), sort_keys=True)
                    + " ".join(m.uci() for m in moves)
                )
                digest = hashlib.sha256(identity.encode()).hexdigest()
                if digest in seen:
                    totals["duplicate_games_skipped"] += 1
                    continue
                seen.add(digest)
                totals["games"] += 1
                own = colors[0]
                counters = Counter()
                alien = False
                for move in moves:
                    if board.turn == own:
                        counters["player_moves"] += 1
                        counters["checks"] += int(board.gives_check(move))
                        counters["captures"] += int(board.is_capture(move))
                        if board.is_castling(move):
                            counters["castles"] += 1
                            counters["castling_fullmove_sum"] += board.fullmove_number
                        if board.fullmove_number <= 15:
                            counters["opening_moves"] += 1
                            counters["opening_checks"] += int(board.gives_check(move))
                        if (
                            own == chess.WHITE
                            and board.fullmove_number == 6
                            and key(board) == alien_key
                        ):
                            counters["alien_opportunities"] += 1
                            if move.uci() == "g5f7":
                                counters["alien_sacrifices"] += 1
                                alien = True
                    board.push(move)
                result = game.headers.get("Result", "*")
                outcome = (
                    "draws"
                    if result == "1/2-1/2"
                    else "wins"
                    if result == ("1-0" if own else "0-1")
                    else "losses"
                    if result in {"0-1", "1-0"}
                    else "unfinished"
                )
                counters[outcome] += 1
                if alien:
                    counters["alien_games"] += 1
                    counters["alien_" + outcome] += 1
                totals.update(counters)
                classes[game.headers.get("TimeControl", "unknown")].update(counters)
                openings[game.headers.get("ECO", "unknown")] += 1
    rates = {
        "checks_per_100_moves": 100 * totals["checks"] / totals["player_moves"]
        if totals["player_moves"]
        else None,
        "captures_per_100_moves": 100 * totals["captures"] / totals["player_moves"]
        if totals["player_moves"]
        else None,
        "mean_castling_fullmove_when_castled": totals["castling_fullmove_sum"] / totals["castles"]
        if totals["castles"]
        else None,
    }
    return {
        "player": player,
        "counts": dict(totals),
        "rates": rates,
        "by_time_control": dict(classes),
        "openings": dict(openings),
        "limitations": "Descriptive decision counts, not evidence that sacrifices are sound or that a style causes wins. Game strength, opponent selection and clocks are confounders. Alien detection requires the exact pre-sacrifice board and Nxf7, accepting Nd2/Nc3 transposition. No player personality or endorsement inference. No neural training performed by this analysis.",
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--pgn", type=Path, nargs="+", required=True)
    p.add_argument("--player", default="witty_alien")
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    report = analyze(a.pgn, a.player)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
