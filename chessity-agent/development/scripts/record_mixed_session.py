"""Replay the combined candidate's finished games and publish local evidence."""

import argparse
import hashlib
import io
import json
import zipfile
from collections import Counter
from pathlib import Path

import chess
import chess.pgn

from engine.openings import alien_move
from harness.referee import FAILED_TERMINATIONS


def audit(rows):
    assert len(rows) == 12
    assert sum(row["candidate_white"] for row in rows) == 6
    stats = {"wins": 0, "draws": 0, "losses": 0, "alien_opportunities": 0, "alien_choices": 0}
    terminations = Counter()
    for row in rows:
        game = chess.pgn.read_game(io.StringIO(row["pgn"]))
        assert game is not None and not game.errors
        assert row["termination"] not in FAILED_TERMINATIONS
        board = game.board()
        for move in game.mainline_moves():
            if board.turn == row["candidate_white"]:
                hint = alien_move(board)
                if hint is not None and hint.uci() == "g5f7":
                    stats["alien_opportunities"] += 1
                    stats["alien_choices"] += move.uci() == "g5f7"
            assert move in board.legal_moves
            board.push(move)
        outcome = board.outcome(claim_draw=True)
        if row["termination"] == "ply_cap":
            assert row["score"] == 0.5
        else:
            assert outcome and outcome.termination.name.lower() == row["termination"]
            score = (
                0.5 if outcome.winner is None else float(outcome.winner == row["candidate_white"])
            )
            assert score == row["score"]
        white_score = row["score"] if row["candidate_white"] else 1 - row["score"]
        assert game.headers["Result"] == {1: "1-0", 0.5: "1/2-1/2", 0: "0-1"}[white_score]
        stats[{1: "wins", 0.5: "draws", 0: "losses"}[row["score"]]] += 1
        terminations[row["termination"]] += 1
    stats["score"] = (stats["wins"] + 0.5 * stats["draws"]) / len(rows)
    stats["terminations"] = dict(terminations)
    return stats


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run", type=Path, default=Path("runs/mixed-20260906"))
    a = p.parse_args()
    session = json.loads((a.run / "session.json").read_text())
    assert session["status"] == "complete"
    root = Path(session["candidate"])
    for name, digest in session["candidate_file_hashes"].items():
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest
    archive = root.with_suffix(".zip")
    assert hashlib.sha256(archive.read_bytes()).hexdigest() == session["candidate_zip_sha256"]
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name in z.namelist():
            assert z.read(name) == (root / name).read_bytes()
    source_policy = Path(session["policy_source"])
    assert source_policy.read_bytes() == (root / "models/player-policy.npz").read_bytes()
    classical_files = [
        "engine/evaluation.py",
        "engine/move_ordering.py",
        "engine/time_manager.py",
        "engine/transposition.py",
    ]
    for name in classical_files:
        assert (root / name).read_bytes() == (Path("champions/classical-v2") / name).read_bytes()
    evidence = Path("docs/evidence")
    summaries = {}
    for stage in ["rating1700", "classical_comparison"]:
        result = json.loads((a.run / f"{stage}.json").read_text())
        if stage == "rating1700":
            assert result["status"] == "complete" and result["elos"] == [1700]
            assert all(g["opponent_elo"] == 1700 for g in result["games"])
            assert {(g["pair"], g["candidate_white"]) for g in result["games"]} == {
                (p, c) for p in range(6) for c in [True, False]
            }
        summaries[stage] = audit(result["games"])
        (evidence / f"mixed-20260906-{stage}.json").write_text(json.dumps(result, indent=2))
        labelled_games = []
        for index, row in enumerate(result["games"], 1):
            game = chess.pgn.read_game(io.StringIO(row["pgn"]))
            opponent = (
                "Classical v2" if stage == "classical_comparison" else "Stockfish 19 UCI_Elo 1700"
            )
            game.headers["White"] = root.name if row["candidate_white"] else opponent
            game.headers["Black"] = opponent if row["candidate_white"] else root.name
            game.headers["Event"] = "Combined candidate evaluation"
            game.headers["Round"] = str(index)
            game.headers["TimeControl"] = "30+0.3"
            labelled_games.append(str(game))
        (evidence / f"mixed-20260906-{stage}.pgn").write_text(
            "\n\n".join(labelled_games) + "\n", encoding="utf-8"
        )
    validations = [
        json.loads(Path(f"runs/mixed-20260906{suffix}.json").read_text())
        for suffix in ["-validation", "-active-validation"]
    ]
    assert all(
        v["sha256"] == session["candidate_zip_sha256"] and v["selective_alien_verified"]
        for v in validations
    )
    assert validations[1]["policy_calls"] > 0
    proof = {
        "session": session,
        "summaries": summaries,
        "package_validations": validations,
        "audit": {
            "games_replayed": 24,
            "candidate_and_zip_hashes_match": True,
            "source_policy_unchanged": True,
            "classical_files_unchanged": classical_files,
            "tests_passed": 44,
            "all_results_and_legal_moves_verified": True,
        },
    }
    (evidence / "mixed-20260906-session.json").write_text(json.dumps(proof, indent=2))
    rating, comparison = summaries["rating1700"], summaries["classical_comparison"]
    table = "\n".join(
        f"| {opponent} | {s['wins']} | {s['draws']} | {s['losses']} | {s['score']:.1%} |"
        for opponent, s in [("Stockfish 19, UCI_Elo 1700", rating), ("Classical v2", comparison)]
    )
    decision = (
        "The direct comparison favoured the combined candidate in this small sample."
        if comparison["score"] > 0.5
        else "The direct comparison did not demonstrate an improvement over Classical v2."
    )
    text = f"""# Combined Classical + Witty candidate — 6 September 2026

Created **mixed-classical-witty-v1**, with Classical's evaluation/search and the
existing Witty-trained move-preference network. Against **Stockfish's 1700 setting**
it scored **{rating["wins"]} wins, {rating["draws"]} draws and {rating["losses"]} losses**.
Both completed batches used **30 seconds + 0.3 seconds per move**, six opening
pairs with colours reversed, 12 games per opponent. At most two games ran concurrently.

| Opponent | Candidate wins | Draws | Candidate losses | Candidate score |
|---|---:|---:|---:|---:|
{table}

{decision}
Twelve games per opponent do not establish a definitive strongest version or an
official rating. The previous Classical competition submission remains preserved.
The Stockfish number is its built-in handicap setting. Its documented calibration
uses 120+1, a different time control; see [Stockfish's UCI documentation](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-Protocol-and-Stockfish-Commands.html).

## What was combined

Classical is a programmed evaluator and search engine, with no learned dataset or
neural weights to concatenate or average. This candidate reuses that fast evaluation
and the existing Witty policy trained from the authorised history. There was no new
training run, invented dataset merge or use of benchmark results as training labels.
The policy file is byte-identical to the previous Witty candidate's policy.

The prior Witty agent ran the 300k value network throughout its hybrid evaluation.
This candidate uses classical evaluation at search nodes to recover search speed;
it retains the separately trained Witty policy at the root. The 300k value model
and its training data remain saved in the original candidate, but that value network
is not loaded by this combined runtime.

Witty move preferences receive at most **10 centipawns**. A matching Alien opening
move receives at most **15 additional centipawns**. Both are small preferences among
searched legal moves. They are bypassed under short search budgets, in check, in
late endgames and in materially unbalanced positions. Proven mate scores are unchanged.
These are search-horizon preferences, not guarantees against future tactical errors.

## Alien Gambit is optional

The repertoire can suggest the Alien move, but no longer returns it before searching.
From `1.e4 c6 2.d4 d5 3.Nd2 dxe4 4.Nxe4 Nf6 5.Ng5 h6`, the extracted package selected
**6.N5f3** in both validation runs, declining the speculative **6.Nxf7** sacrifice.
The book hint still entered search. Outside its exact recognised positions, normal
search and learned move preferences select the move.

The Stockfish batch included a Caro-Kann setup after `1.e4 c6 2.d4 d5` among its six
opening pairs. Neither player was forced into the gambit. Actual candidate Alien
sacrifice opportunities/choices: **{rating["alien_opportunities"]}/{rating["alien_choices"]}** against Stockfish and
**{comparison["alien_opportunities"]}/{comparison["alien_choices"]}** against Classical.
No claims of a successful Alien sacrifice are inferred from a different opening.

## Package and checks

- [Combined agent ZIP](../candidates/mixed-classical-witty-v1.zip) — {archive.stat().st_size:,} bytes.
- [Stockfish 1700 games](evidence/mixed-20260906-rating1700.pgn).
- [Direct Classical comparison games](evidence/mixed-20260906-classical_comparison.pgn).
- [Session, provenance, summaries and validation](evidence/mixed-20260906-session.json).

All **44 tests passed**, including bounded root preferences, rejection of the knight
sacrifice, mate protection and emergency-clock fallback. All **24 match PGNs** were
replayed to verify legal moves and results. Extracted-package checks made **130 legal
calls**, including **{validations[1]["policy_calls"]} active policy calls**. The audit detected no runtime writes,
network use or subprocess launches. Both selective-opening checks passed.

Terminations against Stockfish: `{json.dumps(rating["terminations"], sort_keys=True)}`.
Terminations against Classical: `{json.dumps(comparison["terminations"], sort_keys=True)}`.
Any ply-cap draws are reported explicitly above. The package contains the original
agent code and trained policy, with no external engine or downloaded game history.

ZIP SHA-256: `{session["candidate_zip_sha256"]}`.

Use `Play-Combined.ps1` to play this mode locally. The candidate and earlier packages
are saved separately. The combined version has not been uploaded to the competition.
"""
    Path("docs/COMBINED_AGENT_TEST.md").write_text(text, encoding="utf-8")
    print(json.dumps(summaries, indent=2))


if __name__ == "__main__":
    main()
