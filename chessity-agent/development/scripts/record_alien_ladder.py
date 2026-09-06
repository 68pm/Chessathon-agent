"""Independently replay completed ladder evidence and write the user-facing report."""

import argparse
import hashlib
import io
import json
from collections import Counter
from pathlib import Path

import chess.pgn

from scripts.alien_rating_ladder import summarize


def audit(report):
    assert report["status"] == "complete", "Ladder is not complete"
    expected = {
        (elo, repeat)
        for elo in report["elos"]
        for repeat in range(1, report["repeats_per_level"] + 1)
    }
    actual = [(r["opponent_elo"], r["repeat"]) for r in report["games"]]
    assert len(actual) == len(expected) and set(actual) == expected
    assert report["summary"] == summarize(report["games"], report["elos"])
    prefix = report["opening"]["opening_uci"]
    for row in report["games"]:
        game = chess.pgn.read_game(io.StringIO(row["pgn"]))
        assert game is not None and not game.errors
        moves = list(game.mainline_moves())
        assert [m.uci() for m in moves[: len(prefix)]] == prefix
        assert [m.uci() for m in moves[len(prefix) :]] == [m["uci"] for m in row["moves"]]
        assert moves[len(prefix)].uci() == "g5f7" and row["alien_sacrifice_played"]
        assert game.headers["BlackElo"] == str(row["opponent_elo"])
        assert game.headers["Termination"] == row["termination"]
        board = game.end().board()
        assert board.fen() == row["final_fen"]
        assert row["played_plies"] == len(row["moves"])
        outcome = board.outcome(claim_draw=True)
        if row["termination"] == "ply_cap":
            assert row["played_plies"] == report["ply_cap"] and row["score"] == 0.5
        else:
            assert outcome and outcome.termination.name.lower() == row["termination"]
            assert row["score"] == (0.5 if outcome.winner is None else float(outcome.winner))
        assert game.headers["Result"] == {1: "1-0", 0.5: "1/2-1/2", 0: "0-1"}[row["score"]]
    return {
        "replayed_games": len(actual),
        "legal_moves_verified": True,
        "terminal_results_verified": True,
        "complete_fixed_schedule_verified": True,
        "alien_sacrifice_verified_every_game": True,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--run", type=Path, default=Path("runs/alien-ladder-20260906"))
    p.add_argument("--out", type=Path, default=Path("docs"))
    a = p.parse_args()
    report = json.loads((a.run / "results.json").read_text())
    verification = audit(report)
    candidate = Path("candidates") / report["candidate"]
    for name, digest in report["candidate_manifest_sha256"].items():
        assert hashlib.sha256((candidate / name).read_bytes()).hexdigest() == digest
    verification["frozen_candidate_files_verified"] = True
    summary = report["summary"]
    highest = summary["highest_nominal_level_defeated"]
    winning = [r for r in report["games"] if r["opponent_elo"] == highest and r["score"] == 1]
    evidence = a.out / "evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    stem = a.run.name
    transcript = a.run / "opponent-configuration-transcript.txt"
    if transcript.exists():
        transcript_text = transcript.read_text()
        assert all(
            f"LimitStrength = True, ELO = {elo}." in transcript_text for elo in report["elos"]
        )
        verification["all_opponent_levels_acknowledged_in_diagnostic_transcript"] = True
        (evidence / f"{stem}-opponent-configuration.txt").write_text(transcript_text)
    (evidence / f"{stem}.json").write_text(json.dumps({**report, "audit": verification}, indent=2))
    (evidence / f"{stem}.pgn").write_text(
        "\n\n".join(r["pgn"] for r in report["games"]) + "\n", encoding="utf-8"
    )
    if winning:
        (evidence / f"{stem}-highest-wins.pgn").write_text(
            "\n\n".join(r["pgn"] for r in winning) + "\n", encoding="utf-8"
        )
    table = "\n".join(
        f"| {r['opponent_elo']} | {r['wins']} | {r['draws']} | {r['losses']} |"
        for r in summary["by_level"]
    )
    high_row = next((r for r in summary["by_level"] if r["opponent_elo"] == highest), None)
    headline = (
        f"The highest setting defeated was **MadChess 3.4 at nominal {highest} Elo**. "
        f"At that level the candidate scored {high_row['wins']} win{'s' if high_row['wins'] != 1 else ''}, "
        f"{high_row['draws']} draws and {high_row['losses']} losses."
        if high_row
        else "The candidate did not defeat any ladder level in this run."
    )
    terminations = dict(Counter(r["termination"] for r in report["games"]))
    accepted = sum(len(r["moves"]) > 1 and r["moves"][1]["uci"] == "e8f7" for r in report["games"])
    text = f"""# Alien Gambit rating ladder — completed {report["updated_utc"][:10]}

{headline}

All **{len(report["games"])} games** finished: **{summary["wins"]} wins, {summary["draws"]} draws, {summary["losses"]} losses**.
Each listed setting was tested {report["repeats_per_level"]} times. Highest setting with a
majority score across its games: **{summary["highest_level_with_majority_score"]}**.

These are MadChess's built-in difficulty labels. Its author explicitly says their
human-rating calibration is unknown. Beating one setting does not give the candidate
that Elo. This opening-only result does not replace the earlier general-position
Stockfish estimate or demonstrate an improvement from training.
See [the author's calibration explanation]({report["calibration_documentation"]}).

| MadChess nominal Elo | Agent wins | Draws | Agent losses |
|---:|---:|---:|---:|
{table}

## What was tested

Candidate: `{report["candidate"]}`, the existing 300k-position hybrid plus the
Witty_Alien move-preference network trained using the 50,000 sampled decisions.
The weights, search and opening repertoire were frozen throughout this ladder.
No new training or promotion of the default competition engine took place.

The starting line comes from [Witty_Alien's downloaded game]({report["opening"]["source_url"]})
on {report["opening"]["source_date"]}:

`1.e4 c6 2.d4 d5 3.Nd2 dxe4 4.Nxe4 Nf6 5.Ng5 h6`

Those ten plies are opening setup. The candidate then independently chose **6.Nxf7
in all {len(report["games"])} games**, using its enabled prepared repertoire. MadChess accepted the sacrifice
with **6...Kxf7 in {accepted} games**. Every subsequent move was played by the engines;
the historical game's remaining moves were not replayed. The position was present
in the policy training data; this is a deliberate repertoire test, not a held-out
position test. The prepared move and the learned policy have separate roles.

Both engines had **{report["base_ms"] / 1000:g} seconds + {report["increment_ms"] / 1000:g} seconds per move** from the setup position.
The candidate was White in every game. Up to {report["concurrent_games"]} games ran concurrently on this computer,
with fresh engine processes each game. MadChess used its untouched release config,
64 MB hash and `UCI_LimitStrength=true`; only `UCI_Elo` changed between levels.
Its advertised supported range was {report["engine_elo_range"][0]}–{report["engine_elo_range"][1]}.
There was no custom weakening, depth override or substituted rating scale.
MadChess's default randomization has no exposed seed setting, so reruns may differ.
The schedule was fixed before results were known, with no extra attempts to chase a win.

## Verification and files

All {verification["replayed_games"]} PGNs were independently replayed to verify legal moves, final positions,
results, the Alien sacrifice and the complete schedule. No invalid games occurred.
Terminations: `{json.dumps(terminations, sort_keys=True)}`.
The configured cap was {report["ply_cap"]} played plies after setup; {terminations.get("ply_cap", 0)} games reached it.
Candidate file hashes still match the manifest saved before play.

- [All games in PGN](evidence/{stem}.pgn)
- [Full results, timings, hashes and replay audit](evidence/{stem}.json)
"""
    if winning:
        text += f"- [Victories at the highest defeated level](evidence/{stem}-highest-wins.pgn)\n"
    text += f"""
The external opponent was obtained from the [official MadChess download page](https://www.madchess.net/downloads/).
It is stored only among local benchmark tools and is not inside the candidate or submission.
Opponent executable SHA-256: `{report["engine_sha256"]}`.
See the [official strength-setting documentation]({report["rating_documentation"]}).

To repeat the same ladder on this computer with a fresh output folder:

```powershell
.\\Test-Alien-Ladder.ps1
```

The original default competition submission remains unchanged.
"""
    (a.out / "ALIEN_RATING_LADDER.md").write_text(text, encoding="utf-8")
    print(json.dumps({"summary": summary, "audit": verification}, indent=2))


if __name__ == "__main__":
    main()
