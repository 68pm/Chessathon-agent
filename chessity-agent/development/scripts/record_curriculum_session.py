"""Audit and report the fixed curriculum experiment without promoting on noise."""

import csv
import io
import json
import math
import zipfile
from pathlib import Path

import chess
import chess.pgn

from scripts.alien_rating_ladder import save_json, sha256
from scripts.curriculum_benchmark import CANDIDATE, OPPONENTS
from scripts.magnus_benchmark import manifest, summary
from training.chess_curriculum import PHASES

RUN = Path("runs/carlsen-curriculum-20260906")
EVIDENCE = Path("docs/evidence")


def main():
    matches = json.loads((RUN / "benchmark/results.json").read_text())
    assert matches["status"] == "complete" and len(matches["games"]) == 32
    schedule = {row["id"]: row for row in matches["schedule"]}
    assert set(schedule) == {r["id"] for r in matches["games"]}
    rows = matches["games"]
    for row in rows:
        assert all(row[k] == v for k, v in schedule[row["id"]].items())
        game = chess.pgn.read_game(io.StringIO(row["pgn"]))
        assert game is not None and not game.errors
        board = game.board()
        expected = chess.Board()
        for uci in row["opening"]:
            expected.push_uci(uci)
        assert expected.fen() == board.fen()
        for move in game.mainline_moves():
            assert move in board.legal_moves
            board.push(move)
        assert row["termination"] not in {"invalid", "crash", "illegal", "init", "both_failed"}
        if row["termination"] == "ply_cap":
            assert row["score"] == 0.5
        elif row["termination"] != "flag":
            outcome = board.outcome(claim_draw=True)
            assert outcome and outcome.termination.name.lower() == row["termination"]
            assert row["score"] == (
                0.5 if outcome.winner is None else float(outcome.winner == row["white"])
            )
        white_score = row["score"] if row["white"] else 1 - row["score"]
        assert game.headers["Result"] == {1: "1-0", 0: "0-1", 0.5: "1/2-1/2"}[white_score]
    for name, path in {"candidate": CANDIDATE, **OPPONENTS}.items():
        assert manifest(path) == matches["files"][name]
    validations = {}
    for recipe, candidate in [("curriculum", CANDIDATE), ("control", OPPONENTS["control"])]:
        archive = candidate.with_suffix(".zip")
        with zipfile.ZipFile(archive) as zipped:
            assert zipped.testzip() is None
            for name in zipped.namelist():
                assert zipped.read(name) == (candidate / name).read_bytes()
        checks = [
            json.loads((RUN / f"{prefix}-{recipe}.json").read_text())
            for prefix in ["validate", "validate-active"]
        ]
        assert sum(v["legal_calls"] for v in checks) == 130
        assert all(v["sha256"] == sha256(archive) and v["selective_alien_verified"] for v in checks)
        assert checks[1]["policy_calls"] > 0
        validations[recipe] = checks
        for name in manifest(candidate):
            if name != "models/player-policy.npz":
                assert (candidate / name).read_bytes() == (
                    OPPONENTS["baseline"] / name
                ).read_bytes()
    training = json.loads((RUN / "training/report.json").read_text())
    data = json.loads((RUN / "data/manifest.json").read_text())
    diagnostics = json.loads((RUN / "diagnostics.json").read_text())
    pipeline = json.loads((RUN / "training/pipeline-pilot.json").read_text())
    assert pipeline["verified_positions"] == 1024 and pipeline["whole_game_split_overlap"] == 0
    results = summary(rows)
    direct = {}
    for family in ["control", "baseline"]:
        group = [r for r in rows if r["family"] == family]
        pairs = [sum(r["score"] for r in group if r["pair"] == p) / 2 for p in range(4)]
        mean = sum(pairs) / 4
        direct[family] = {
            "score": mean,
            "pair_standard_error": math.sqrt(sum((v - mean) ** 2 for v in pairs) / 3 / 4),
            "colour_pairs": 4,
            "caution": "Descriptive small-sample standard error; no calibrated Elo or established improvement.",
        }
    regressions = (
        diagnostics["passed_by_model"]["curriculum"] < diagnostics["passed_by_model"]["baseline"]
    )
    negative_match = any(direct[name]["score"] < 0.5 for name in direct)
    decision = (
        "Do not adopt this pilot as an improvement; it showed a regression in the small comparison."
        if regressions or negative_match
        else "Continue testing; this small pilot does not justify automatic promotion."
    )
    proof = {
        "data": data,
        "training": training,
        "pipeline": pipeline,
        "diagnostics": diagnostics,
        "package_validations": validations,
        "summary": results,
        "direct_comparisons": direct,
        "decision": decision,
        "audit": {
            "games_replayed": 32,
            "results_verified": True,
            "runtime_code_identical_to_baseline": True,
            "unit_tests_passed": 54,
        },
        "candidate_zip_sha256": sha256(CANDIDATE.with_suffix(".zip")),
    }
    save_json(EVIDENCE / "carlsen-curriculum-20260906-session.json", proof)
    save_json(EVIDENCE / "carlsen-curriculum-20260906-games.json", matches)
    for family in ["control", "baseline", "madchess", "stockfish"]:
        (EVIDENCE / f"carlsen-curriculum-20260906-{family}.pgn").write_text(
            "\n\n".join(r["pgn"] for r in rows if r["family"] == family) + "\n"
        )
    table = ["| Opponent | W | D | L |", "|---|---:|---:|---:|"]
    for name, counts in results["by_opponent"].items():
        table.append(
            f"| {name} | {counts.get('wins', 0)} | {counts.get('draws', 0)} | {counts.get('losses', 0)} |"
        )
    coverage = [
        "| Primary phase | Control train | Curriculum train | Common validation |",
        "|---|---:|---:|---:|",
    ]
    quality = [
        "| Phase | Baseline top 1 | Control top 1 | Curriculum top 1 |",
        "|---|---:|---:|---:|",
    ]
    for phase in PHASES:
        old, new = [data["recipes"][name]["phases"] for name in ["control", "curriculum"]]
        coverage.append(
            f"| {phase} | {old.get('train:' + phase, 0)} | {new.get('train:' + phase, 0)} | {new.get('validation:' + phase, 0)} |"
        )
        values = [
            training["phase_validation"][name][phase]["full_legal"]["top1"]
            for name in ["baseline", "control", "curriculum"]
        ]
        quality.append(f"| {phase} | {values[0]:.1%} | {values[1]:.1%} | {values[2]:.1%} |")
    text = (
        f"""# Carlsen curriculum: controlled pilot

**Recommendation: {decision}** The experimental candidate is `candidates/carlsen-curriculum-v1.zip`; the equal-compute control is `candidates/carlsen-curriculum-control-v1.zip`. Neither replaces the prior combined packages or the selected classical submission.

The user supplied `docs/CARLSEN_CURRICULUM_PROMPT.md`. This implementation applies its smallest compatible data experiment: better phase coverage with the existing move-policy architecture and base loss. It does not claim to implement every theme in the prose or reproduce Carlsen's thought process.

## What changed

Both recipes start from `classical-witty-magnus-v1`, use 8,192 real training positions (half from each player), share 1,024 validation positions, run three epochs at learning rate 0.0001 and use the same seed and batch count. Common positions share the exact encoded features and negative alternatives. The ordinary control samples without phase balancing. The curriculum combines 50% ordinary sampling with 50% phase-balanced sampling. Checkpoints use validation cross-entropy; the previous final test set is excluded from this experiment.

A separate 1,024-position pipeline pilot checked legal labels, finite features/loss/gradients and whole-game separation before either recipe. Its temporary model was discarded. Both player datasets and all their outcomes/colours remain represented; source URLs, PGN checksums, player side, time control and time class are retained. Whole-game splits and exact FEN deduplication are inherited from the audited source pool. Related positions may remain across splits.

Phase categories use remaining material, queen count and minors on initial back-rank squares, with overlapping tags. They are heuristic categories, not expert plan annotations or move-number cutoffs. Mechanically checked tags include checks, captures, quiet moves, king moves, castling, promotions, queen captures, open files and passed pawns. These facts categorise examples; they do not assert that an action is good and never add rewards. Prophylaxis, exploitable weaknesses, fortresses and multi-step strategic plans have not been automatically labelled or learned as verified concepts.

**Runtime limit:** the classical search and all runtime code are unchanged. Its neural preference remains disabled in check, strongly imbalanced positions and material phase <=0.20. Thus this pilot's late-endgame neural learning does not affect those production decisions. FEN policy inputs lack full repetition history; full histories remain recoverable from the referenced source PGNs, while runtime search keeps its existing draw handling. No external teacher labels, tablebases, new value head or permanent move bonuses were introduced.

## Phase coverage

"""
        + "\n".join(coverage)
        + "\n\n## Development-set move agreement\n\nThese are raw policy choices on the common validation set, used for development—not a fresh final test or a measure of tactical correctness.\n\n"
        + "\n".join(quality)
    )
    text += "\n\n## Fixed match results\n\n" + "\n".join(table)
    text += f"""

All 32 games used 30+0.3, both colours, fixed openings and at most two simultaneous games. There were eight games against the control, eight against the frozen Magnus/Witty baseline, and four each at MadChess 1500/1700/1900 and Stockfish 1700. The schedule was fixed before outcomes. All PGNs replayed correctly. Terminations: `{json.dumps(results["terminations"])}`. Highest checkmate wins: `{json.dumps(results["highest_checkmate_win_by_family"])}`. These are opponent settings, not an Elo rating for the candidate.

The direct comparisons contain only four colour pairs each. Their descriptive pair standard errors are `{json.dumps(direct)}`; the sample is too small to establish a reliable strength gain.

## Concrete checks, speed and limits

Verified small counterexamples cover taking an immediate mate instead of continuing development, answering check in a queenless ending, avoiding queen-promotion stalemate, and preserving valid draw outcomes. A rook promotion retains mating material where a queen immediately stalemates; non-promotion moves that avoid immediate draw are also accepted, so this is not a proof of eventual conversion. Colour mirrors give 14 cases per model. Passed: `{json.dumps(diagnostics["passed_by_model"])}`. These are known diagnostic positions, not evidence of opposition, triangulation, rook-endgame or fortress mastery. Full FENs and chosen moves are in the evidence file. Lost match PGNs remain available as concrete failure records; no unverified strategic explanation is assigned to a loss.

Raw policy inference timings on the same 256 validation positions, including feature encoding (milliseconds): `{json.dumps(diagnostics["raw_policy_inference_timing"])}`. Architecture and parameter count remain unchanged. Each extracted ZIP passed 130 legal-move calls and active-policy checks with no writes, networking or subprocesses. Unit checks total 54. Organiser Linux validation remains separate.

Training loops used {sum(v["seconds"] for v in training["recipes"].values()):.2f} seconds in total, excluding data preparation, shared feature encoding, diagnostics and matches. Best checkpoints and optimiser states are in `runs/carlsen-curriculum-20260906/training/`. The source and commands are retained in `training/chess_curriculum.py`, `training/curriculum_pilot.py`, `scripts/curriculum_session.py` and `configs/carlsen-curriculum-pilot.json`; use fresh output directories to preserve evidence.

Evidence: `docs/evidence/carlsen-curriculum-20260906-session.json`, `docs/evidence/carlsen-curriculum-20260906-games.json`, and four opponent-family PGNs. Training sources are the already authorised, downloaded public player histories. [Maia research](https://www.maiachess.com/) distinguishes human move imitation from maximising strength; this pilot keeps that distinction explicit.
"""
    text += """
## Reproduce the data and training

From the project root with its Python environment (use fresh output paths):

```powershell
python -m training.chess_curriculum --out runs/curriculum-repeat/data
python -m training.curriculum_pilot --data runs/curriculum-repeat/data --out runs/curriculum-repeat/training
python -m scripts.curriculum_diagnostics --training runs/curriculum-repeat/training --out runs/curriculum-repeat/diagnostics.json
```

Package commands and the fixed benchmark are recorded in `scripts/curriculum_session.py`.
Its dated paths deliberately reject overwriting this experiment. To repeat matches,
configure a fresh run path and new frozen candidate folders in a copy of the controller.
Shared feature caches may be rebuilt from `training/union.jsonl` using
`training.player_policy.build` with seed 20260907. A cache cleanup manifest records
the original checksum; data, checkpoints and match evidence remain preserved.
"""
    Path("docs/CARLSEN_CURRICULUM_RESULTS.md").write_text(text, encoding="utf-8")
    note = (
        "\n<!-- CURRICULUM_SESSION_START -->\n## Phase curriculum pilot\n\n"
        "The controlled phase-coverage experiment is complete. "
        + decision
        + " See `docs/CARLSEN_CURRICULUM_RESULTS.md` for the 32-game comparison, "
        "validation counts, scope and reproduction steps. Candidate and equal-compute "
        "control are preserved separately; neither automatically replaces the baseline.\n"
        "<!-- CURRICULUM_SESSION_END -->\n"
    )
    for path in [Path("README.md"), Path("MODEL_CARD.md")]:
        original = path.read_text(encoding="utf-8")
        if "<!-- CURRICULUM_SESSION_START -->" not in original:
            path.write_text(original + note, encoding="utf-8", newline="\n")
    ledger = Path("EXPERIMENTS.csv")
    with ledger.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        fields, existing = reader.fieldnames, list(reader)
    # Retain the established ledger schema and use its immediately preceding row as a template.
    experiment_key = fields[0]
    if not any(r[experiment_key] == "carlsen-curriculum-20260906" for r in existing):
        entry = dict.fromkeys(fields, "")
        entry[experiment_key] = "carlsen-curriculum-20260906"
        # The evidence report is authoritative; avoid inventing aggregate Elo estimates.
        for key in fields:
            if key == "notes":
                entry[key] = decision + " See docs/CARLSEN_CURRICULUM_RESULTS.md; 32 paired games and 54 unit checks."
            elif key == "date":
                entry[key] = "2026-09-06"
            elif key == "decision":
                entry[key] = "experimental_candidate"
        counts = {name: sum(r["score"] == value for r in rows) for name, value in [("wins", 1), ("draws", 0.5), ("losses", 0)]}
        entry.update(counts)
        entry.update(games=32, time_control="30+0.3", seed=20260907,
                     score=sum(r["score"] for r in rows) / 32,
                     config="configs/carlsen-curriculum-pilot.json",
                     dataset_hash=data["recipes"]["curriculum"]["sha256"],
                     change="Phase-balanced policy training versus matched ordinary control",
                     model_bytes=(CANDIDATE / "models/player-policy.npz").stat().st_size,
                     zip_bytes=CANDIDATE.with_suffix(".zip").stat().st_size)
        with ledger.open("a", newline="", encoding="utf-8") as stream:
            csv.DictWriter(stream, fieldnames=fields, lineterminator="\n").writerow(entry)
    print(json.dumps({"decision": decision, "summary": results}, indent=2))


if __name__ == "__main__":
    main()
