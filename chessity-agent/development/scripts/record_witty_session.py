"""Record a completed player-training session without altering previous rating evidence."""

import hashlib
import io
import json
import math
import zipfile
from collections import Counter
from pathlib import Path

import chess
import chess.pgn

from training.history_batches import load_json, write_json


def game_style(rows):
    totals = {"candidate": Counter(), "baseline": Counter()}
    for row in rows:
        game = chess.pgn.read_game(io.StringIO(row["pgn"]))
        if game.errors:
            raise ValueError("Invalid comparison PGN")
        board = game.board()
        own = chess.WHITE if row["candidate_white"] else chess.BLACK
        for move in game.mainline_moves():
            if move not in board.legal_moves:
                raise ValueError("Illegal recorded move")
            key = "candidate" if board.turn == own else "baseline"
            totals[key]["moves"] += 1
            totals[key]["checks"] += int(board.gives_check(move))
            totals[key]["captures"] += int(board.is_capture(move))
            if board.fullmove_number <= 15:
                totals[key]["opening_moves"] += 1
                totals[key]["opening_checks"] += int(board.gives_check(move))
            board.push(move)
    return {
        name: {
            **counts,
            "checks_per_100_moves": 100 * counts["checks"] / counts["moves"],
            "captures_per_100_moves": 100 * counts["captures"] / counts["moves"],
        }
        for name, counts in totals.items()
    }


def main():
    run = Path("runs/witty-style-20260906")
    status = load_json(run / "session-status.json")
    if status["status"] != "complete":
        raise ValueError("Session is not complete")
    active_validation = load_json(run / "active-policy-validation.json")
    if active_validation["policy_calls"] < 1:
        raise ValueError("Active policy inference was not exercised by package checks")
    history = Path(status["history_export"])
    manifest = load_json(history / "manifest.json")
    missing_audit = load_json(run / "missing-pgn-audit.json")
    analysis = load_json(history / "style-analysis.json")
    samples = load_json(history / "style-samples.manifest.json")
    effect = load_json(run / "policy-effect.json")
    if effect["sample_sha256"] != samples["sha256"]:
        raise ValueError("Controlled policy check used different player samples")
    evaluation = load_json(run / "policy/evaluation.json")
    candidate = Path("candidates/witty-300k-hybrid-v1")
    if (
        hashlib.sha256((candidate / "models/player-policy.npz").read_bytes()).hexdigest()
        != evaluation["weights_sha256"]
    ):
        raise ValueError("Candidate policy differs from evaluated training weights")
    if (candidate / "models/value.npz").read_bytes() != Path("models/value-300k.npz").read_bytes():
        raise ValueError("Candidate value network differs from the preserved 300k network")
    with zipfile.ZipFile(candidate.with_suffix(".zip")) as archive:
        if archive.testzip() is not None or any(
            archive.read(name) != (candidate / name).read_bytes() for name in archive.namelist()
        ):
            raise ValueError("Benchmarked runtime differs from the audited package")
    metrics = load_json(run / "policy/metrics.json")
    comparison = load_json(run / "comparison.json")
    rating = load_json(run / "rating.json")
    if rating["status"] != "complete" or len(rating["games"]) != 12:
        raise ValueError("Rating games incomplete")
    pgns = []
    for row in rating["games"]:
        game = chess.pgn.read_game(io.StringIO(row["pgn"]))
        if game.errors:
            raise ValueError("Invalid rating PGN")
        board = game.end().board()
        if row["termination"] != "ply_cap":
            outcome = board.outcome(claim_draw=True)
            if outcome is None or outcome.result() != game.headers["Result"]:
                raise ValueError("PGN outcome does not match recorded result")
        pgns.append(row["pgn"])
    rows = [json.loads(line) for line in (history / "style-samples.jsonl").read_text().splitlines()]
    seen, groups = set(), {}
    for row in rows:
        key = " ".join(row["fen"].split()[:4])
        if key in seen or groups.setdefault(row["game_id"], row["split"]) != row["split"]:
            raise ValueError("Sample split/deduplication failure")
        seen.add(key)
    name = "witty-300k-hybrid-v1"
    summary = rating["summary"][name]
    point = summary["nominal_handicap_scale_estimate"]
    low, high = summary["approximate_uncertainty_envelope"]
    band = f"{math.floor(low / 100) * 100 if low is not None else 'unbounded'} to {math.ceil(high / 100) * 100 if high is not None else 'unbounded'}"
    style = game_style(comparison["games"])
    report = {
        "session": status,
        "download": {
            k: manifest[k]
            for k in [
                "unique_games",
                "pgn_games",
                "duplicates_removed",
                "missing_pgn_games",
                "source_digest",
            ]
        },
        "months": len(manifest["sources"]),
        "missing_pgn_audit": missing_audit,
        "parts": len(manifest["parts"]),
        "player_analysis": analysis,
        "sample_manifest": samples,
        "policy_evaluation": evaluation,
        "epochs": len(metrics["epochs"]),
        "comparison": {k: v for k, v in comparison.items() if k != "games"},
        "comparison_style": style,
        "controlled_policy_effect": {k: v for k, v in effect.items() if k != "pairs"},
        "rating": summary,
        "rating_terminations": dict(Counter(r["termination"] for r in rating["games"])),
        "rating_rounded_band": band,
        "validation": load_json(run / "package-validation.json"),
        "active_policy_validation": active_validation,
        "value_sha256": hashlib.sha256(Path("models/value-300k.npz").read_bytes()).hexdigest(),
        "sample_audit": {
            "positions": len(rows),
            "whole_game_groups": len(groups),
            "duplicate_fens": 0,
        },
    }
    evidence = Path("docs/evidence")
    write_json(evidence / "witty-training-session.json", report)
    write_json(evidence / "witty-policy-effect.json", effect)
    write_json(evidence / "witty-rating-games.json", rating)
    (evidence / "witty-rating-games.pgn").write_text("\n\n".join(pgns), encoding="utf-8")
    write_json(evidence / "witty-comparison-games.json", comparison)
    (evidence / "witty-comparison-games.pgn").write_text(
        "\n\n".join(r["pgn"] for r in comparison["games"]), encoding="utf-8"
    )
    observed = analysis["counts"]
    heldout = evaluation["full_legal_choices"]
    best = min(metrics["epochs"], key=lambda r: r["validation"]["cross_entropy"])
    text = f"""# Player-style training completed — 6 September 2026

Downloaded **{manifest["unique_games"]:,} unique available games** across {len(manifest["sources"])} monthly
archives, saved as {len(manifest["parts"]):,} parts of at most 50 games. There were
{manifest["missing_pgn_games"]} missing PGNs and {manifest["duplicates_removed"]} duplicate records.
All {missing_audit["rules"].get("bughouse", 0)} bughouse records without PGN are retained
in the raw JSON and excluded from standard-chess move training.
The user confirmed written Chess.com authorisation in this task before collection.
Only completed games exposed by the public index at collection time are covered;
private, deleted, unexposed and later games are outside this snapshot.

## What was trained

The original 300,000-position value-training run was already complete. Its self-trained
value weights are retained. This session trained a separate original 935–64–32–1
move-ranking neural network on **{len(rows):,} recorded Witty_Alien decisions**, sampled
across the entire history. Split counts: {evaluation["splits"]["train"]:,} training,
{evaluation["splits"]["validation"]:,} validation and {evaluation["splits"]["test"]:,} test.
These are positions/decisions, **not 300,000 self-play games**.

Each training target is his actual legal move against up to four sampled legal alternatives.
Checks/captures are prioritised within each game; the sample reserves the exact Alien
sacrifice position when available. Whole-game hashes set the splits before sampling;
the final sample contains no repeated exact normalised FEN. Related positions can
remain across splits. Synthetic downloader fixtures were not used for training.

Completed {len(metrics["epochs"])} epochs, selecting epoch {best["epoch"]} using validation
cross-entropy only. On {heldout["counts"]["positions"]:,} held-out positions evaluated against
**all legal moves**, the policy matched his recorded move {100 * heldout["top1"]:.1f}% of
the time (uniform legal choice: {100 * heldout["uniform_top1"]:.1f}%), with top-three agreement
{100 * heldout["top3"]:.1f}%. This measures imitation, not strength or tactical soundness.
On those test positions the raw policy chose checks {heldout["counts"]["selected_checks"] / 10:.1f}%
and captures {heldout["counts"]["selected_captures"] / 10:.1f}% of the time, versus
{heldout["counts"]["observed_checks"] / 10:.1f}% and {heldout["counts"]["observed_captures"] / 10:.1f}%
for the recorded player moves. This shows a forcing-move bias in the raw policy;
the final engine still evaluates those moves through search.

The policy adds at most 20 centipawns to root-search preferences in roughly balanced
middlegames. It is disabled in check, under 50 ms of search time, in late endgames and
when the classical evaluation exceeds three pawns. This is a limit at the current
search horizon, not a guarantee against future blunders. Proven mate scores are not
modified. The Alien Gambit remains an explicit prepared repertoire; its inclusion is
separate from learning broader move preferences.

## Observed history

Analysed {observed.get("games", 0):,} matching standard-chess games. Check frequency was
{analysis["rates"]["checks_per_100_moves"]:.2f} per 100 moves; capture frequency was
{analysis["rates"]["captures_per_100_moves"]:.2f}. Exact Alien Gambit detection found
{observed.get("alien_sacrifices", 0):,} Nxf7 sacrifices in {observed.get("alien_opportunities", 0):,}
opportunities. Counts accept Nd2/Nc3 transposition but do not cover every related gambit.
These descriptive counts do not establish that sacrifices are objectively sound.

## Fresh match results and estimated Elo

At 3 seconds + 0.05 seconds per move, the new candidate scored
**{comparison["wins"]} wins / {comparison["draws"]} draws / {comparison["losses"]} losses**
against the previous 300k hybrid in 12 games with colours reversed across six openings.
Observed checks per 100 moves were {style["candidate"]["checks_per_100_moves"]:.2f} for the
new candidate and {style["baseline"]["checks_per_100_moves"]:.2f} for the baseline.
This small sample does not establish a stable style change or justify promotion.

In a separate controlled check on {effect["completed_pairs"]} held-out positions at
equal completed search depth two, the policy changed {effect["changed_moves"]} moves.
Baseline/policy check counts were {effect["totals"]["baseline"]["checks"]}/{effect["totals"]["learned_policy"]["checks"]},
capture counts were {effect["totals"]["baseline"]["captures"]}/{effect["totals"]["learned_policy"]["captures"]},
and matches to the player's recorded choice were
{effect["totals"]["baseline"]["observed_move_matches"]}/{effect["totals"]["learned_policy"]["observed_move_matches"]}.
The repertoire was disabled for this check. These small differences show that the
policy influences search, but do not establish a consistent increase in aggression.

The external benchmark completed **{summary["wins"]} wins / {summary["draws"]} draws /
{summary["losses"]} losses** in 12 games at **30 seconds + 0.3 seconds per move** against
Stockfish 19 handicap settings 1320, 1500 and 1700, four games per setting. There were no
illegal-move, crash or clock failures. The fitted estimate is
**{round(point) if point is not None else "unbounded"} on that nominal handicap scale**, with a broad approximate
band of **{band}**. This is **not a Chess.com, Lichess, FIDE or official Chessathon rating**.

The band combines a colour-pair bootstrap stratified by opponent setting and a
conservative score interval, rounded outward to 100 points. It is a small-sample
approximation, not guaranteed coverage, and excludes calibration and hardware error.
Stockfish documents its handicap calibration at 120+1, different from these clocks.
The opening schedule and one opponent family also limit generalisation.
The results do not establish a strength gain or a consistent increase in attacking
play. The previous 1731 estimate came from a separate small match batch; its difference
from this estimate is not a controlled measurement of a rating change.

## Use the trained candidate

Run `Play-Trained-Aggressive.ps1`. The engine plays White with the learned policy and
Alien repertoire. Its portable runtime is `candidates/witty-300k-hybrid-v1.zip`.
The classical competition champion remains preserved. No third-party engine binary,
published neural weights or downloaded game history is in the candidate runtime.

All history is under `data/witty_alien-history/`; `latest.json` identifies the exact
snapshot. Training checkpoints, optimiser state, logs and full match evidence are under
`runs/witty-style-20260906/`. Compact audited evidence is in
`docs/evidence/witty-training-session.json`, with full PGNs alongside it.

Sources: [Chess.com public archive API](https://www.chess.com/news/view/published-data-api),
[Stockfish handicap documentation](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-Protocol-and-Stockfish-Commands.html),
[CC0 value-training data](https://database.lichess.org/).
"""
    Path("docs/WITTY_TRAINING_SESSION.md").write_text(text, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "games_downloaded": manifest["unique_games"],
                "policy_positions": len(rows),
                "rating": summary,
                "rounded_band": band,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
