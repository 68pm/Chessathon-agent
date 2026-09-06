"""Publish completed benchmark evidence and a deliberately qualified rating report."""

import argparse
import csv
import hashlib
import io
import json
import math
from pathlib import Path

import chess.pgn

from scripts.rating_benchmark import summarize


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, default=Path("runs/rating-300k-30s.json"))
    a = p.parse_args()
    report = json.loads(a.input.read_text())
    if report["status"] != "complete":
        raise ValueError("Benchmark must finish before publishing final results")
    for row in report["games"]:
        game = chess.pgn.read_game(io.StringIO(row["pgn"]))
        assert game and not game.errors
        board = game.end().board()
        if row["termination"] != "ply_cap":
            outcome = board.outcome(claim_draw=True)
            assert outcome and outcome.termination.name.lower() == row["termination"]
            expected = (
                0.5 if outcome.winner is None else float(outcome.winner == row["candidate_white"])
            )
            assert expected == row["score"]
    report["summary"] = summarize(report["games"])
    report["original_log_sha256"] = hashlib.sha256(a.input.read_bytes()).hexdigest()
    report["statistics_note"] = (
        "Recomputed from completed games with scripts/rating_benchmark.py; small-sample Wilson envelope and opponent-level-stratified pair bootstrap added after launch, without changing game schedule or results."
    )
    folders = {
        "classical-v2": Path("champions/classical-v2"),
        "candidate-300000-hybrid": Path("runs/unattended-20260905-away/candidate-300000-hybrid"),
    }
    report["agent_file_hashes"] = {
        name: {
            f.relative_to(folder).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(folder.rglob("*"))
            if f.is_file() and f.suffix in {".py", ".json", ".npz"} and "__pycache__" not in f.parts
        }
        for name, folder in folders.items()
    }
    evidence = Path("docs/evidence/rating-300k-30s.json")
    evidence.write_text(json.dumps(report, indent=2))
    evidence.with_suffix(".pgn").write_text(
        "\n\n".join(row["pgn"] for row in report["games"]) + "\n", encoding="utf-8"
    )
    lines = [
        "# 300k training and provisional rating benchmark",
        "",
        "## Training completed",
        "",
        "The 300,000-position dataset run completed on 5 September 2026. It contains 240,436",
        "training, 28,176 validation and 31,388 held-out test positions. The selected 128-unit",
        "value network achieved validation MSE 0.106637 and held-out MSE 0.114548. These are",
        "prediction errors, not Elo. Full details and hashes are in MODEL_CARD.md.",
        "",
        "At the earlier 3+0.05 promotion screen the hybrid scored 3W/4D/5L against classical v2;",
        "the neural-only version scored 1W/5D/6L. Neither passed that screen. The trained hybrid",
        "is available locally, while the classical competition package remains preserved.",
        "",
        "## External-opponent results",
        "",
        f"Completed {len(report['games'])} games at {report['base_ms'] / 1000:g} seconds + {report['increment_ms'] / 1000:g} seconds per move.",
        "Stockfish 19 used one search thread, 64 MB hash, UCI_LimitStrength=true, Move Overhead=20ms,",
        "and nominal UCI_Elo settings 1320, 1500 and 1700. Each candidate played six opening",
        "pairs with colours reversed: twelve games, four per level. Neither candidate used",
        "the Alien repertoire in this general-rating benchmark. No evaluation adjudication was used.",
        "",
        "| Agent | W / D / L | Score | Nominal-scale estimate | Broad approximate band |",
        "| --- | --- | ---: | ---: | --- |",
    ]
    for name, stats in report["summary"].items():
        rating = stats["nominal_handicap_scale_estimate"]
        low, high = stats["approximate_uncertainty_envelope"]
        band = f"{math.floor(low / 100) * 100 if low is not None else 'unbounded'} to {math.ceil(high / 100) * 100 if high is not None else 'unbounded'}"
        estimate = str(round(rating)) if rating is not None else "no finite estimate"
        lines.append(
            f"| {name} | {stats['wins']} / {stats['draws']} / {stats['losses']} | {stats['score']:.1%} | {estimate} | {band} |"
        )
    lines += [
        "",
        "The bands are rounded outwards to 100-point steps. They describe uncertainty on the",
        "nominal opponent handicap scale only. They are **not Chess.com, Lichess, FIDE or official",
        "Chessathon ratings**, and do not establish advanced/master strength. A model trained",
        "on more positions is not automatically a stronger player.",
        "",
        "| Agent | Opponent setting | Games | Score |",
        "| --- | ---: | ---: | ---: |",
    ]
    for name, stats in report["summary"].items():
        for elo, group in stats["by_opponent"].items():
            lines.append(f"| {name} | {elo} | {group['games']} | {group['score']:.1%} |")
    lines += [
        "",
        "## How to read the estimate",
        "",
        "We fit the Elo logistic expected-score equation to the actual scores across nominal",
        "opponent settings. A descriptive 3,000-resample bootstrap keeps each colour pair",
        "together within each opponent-level stratum. To avoid a falsely narrow small-sample",
        "interval, the reported envelope is",
        "the union with a Wilson score band using the number of pairs as effective sample size.",
        "This nominal 95% construction is an approximation, not a guarantee of 95% coverage.",
        "Raw intervals and all game records are in `evidence/rating-300k-30s.json`; replayable",
        "games are in `evidence/rating-300k-30s.pgn`. Boundary estimates remain unbounded.",
        "",
        "There are only six opening pairs per bot and one opponent family. Opponent levels",
        "are paired with fixed openings, so opening and level effects are partly confounded.",
        "Stockfish's handicap move selection is randomized; reruns need not produce identical games.",
        "The tests ran locally on an Intel i5-12450H under Windows, with ordinary system load",
        "and brief development checks. No dedicated-core or equal-hardware calibration is claimed.",
        "",
        "Current [Stockfish UCI documentation](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-Protocol-and-Stockfish-Commands.html)",
        "describes its handicap calibration at 120+1 with a CCRL 40/4 anchor. Our 30+0.3 clock differs;",
        "hardware, time control and artificial move selection add **uncertainty outside the reported",
        "band**. The [Stockfish FAQ](https://official-stockfish.github.io/docs/stockfish-wiki/Stockfish-FAQ.html)",
        "explains why ratings depend on the opponent pool and match conditions. The nominal",
        "settings should not be treated as certified human-rated opponents.",
        "",
        "## Attacking option and player history",
        "",
        "`Play-Alien.ps1` runs the trained hybrid with independently prepared Alien Gambit moves.",
        "Local analysis and limitations are in ALIEN_GAMBIT.md. This optional mode has no established",
        "rating; the table above must not be represented as its measured rating.",
        "",
        "No Witty_Alien game history was downloaded or used. The requested automated collection",
        "and player-derived training remain pending written Chess.com authorisation. The prepared",
        "serial importer and synthetic-data-tested analysis are documented in WITTY_ALIEN_PERMISSION_NOTE.md.",
        "",
        "## Verification",
        "",
        "25 automated tests passed, including opening legality/transposition handling, PGN deduplication",
        "and Alien detection, statistical sanity checks, engine legality and network gradients.",
        "The final Alien package passed 100 extracted-process legal calls under the no-write,",
        "no-network, no-subprocess audit. Both local play launchers were smoke-tested. Benchmark",
        "PGNs were replayed and their terminal results checked before this report was produced.",
        "No external engine or published weights are shipped, no competition upload occurred,",
        "and no paid compute was used.",
        "",
    ]
    Path("docs/RATING_AND_300K.md").write_text("\n".join(lines), encoding="utf-8")
    with Path("EXPERIMENTS.csv").open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        fields, existing = reader.fieldnames, list(reader)
    known = {row["experiment_id"] for row in existing}
    additions = []
    for size in [100000, 300000]:
        root = Path("runs/unattended-20260905-away")
        metadata = json.loads((root / f"data-{size}/metadata.json").read_text())
        for hidden in [64, 128]:
            metrics = json.loads((root / f"value-{size}-{hidden}/metrics.json").read_text())
            best = min(metrics["epochs"], key=lambda e: e["validation_mse"])
            additions.append(
                {
                    "experiment_id": f"train-{size}-{hidden}",
                    "date": "2026-09-05",
                    "change": f"{size}-position dataset, hidden={hidden}",
                    "seed": 20260905,
                    "dataset_hash": metadata["dataset_sha256"],
                    "decision": "candidate_only",
                    "notes": f"Best epoch {best['epoch']}; validation MSE {best['validation_mse']}; {len(metrics['epochs'])} epochs; see runs/unattended-20260905-away",
                }
            )
    for name, stats in report["summary"].items():
        additions.append(
            {
                "experiment_id": f"sf19-30s-{name}",
                "date": "2026-09-05",
                "change": "Nominal handicap-scale benchmark",
                "games": stats["games"],
                "time_control": "30+0.3",
                "wins": stats["wins"],
                "draws": stats["draws"],
                "losses": stats["losses"],
                "score": stats["score"],
                "decision": "provisional_rating_only",
                "notes": "See docs/evidence/rating-300k-30s.json for source hashes and conditional uncertainty; no human/site rating",
            }
        )
    with Path("EXPERIMENTS.csv").open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        for row in additions:
            if row["experiment_id"] not in known:
                writer.writerow(row)
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
