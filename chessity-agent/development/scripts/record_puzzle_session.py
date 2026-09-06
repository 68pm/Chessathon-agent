"""Audit the completed pilot and report improvements, regressions and unresolved scope."""

import io
import json
import shutil
import zipfile
from collections import Counter
from pathlib import Path

import chess
import chess.pgn

from scripts.alien_rating_ladder import save_json, sha256

RUN = Path("runs/puzzle-pilot-20260906")
EVIDENCE = Path("docs/evidence")


def main():
    state = json.loads((RUN / "session.json").read_text())
    assert state["status"] == "complete"
    data = json.loads((RUN / "data/manifest.json").read_text())
    audit = json.loads((RUN / "data/audit.json").read_text())
    training = json.loads((RUN / "training/report.json").read_text())
    evaluation = json.loads((RUN / "evaluation.json").read_text())
    rollouts = json.loads((RUN / "rollouts.json").read_text())
    assert evaluation["status"] == rollouts["status"] == "complete"
    matches = {}
    for name in ["baseline", "control"]:
        match = json.loads((RUN / f"matches-{name}.json").read_text())
        assert len(match["games"]) == 8 and match["base_ms"] == 30000 and match["increment_ms"] == 300
        for row in match["games"]:
            game = chess.pgn.read_game(io.StringIO(row["pgn"]))
            assert game and not game.errors
            board = game.board()
            assert board.fen() == row["fen"]
            for move in game.mainline_moves():
                assert move in board.legal_moves
                board.push(move)
            assert row["termination"] not in {"illegal", "crash", "init", "void"}
            if row["termination"] not in {"flag", "ply_cap"}:
                outcome = board.outcome(claim_draw=True)
                assert outcome and outcome.termination.name.lower() == row["termination"]
                expected = 0.5 if outcome.winner is None else float(outcome.winner == row["candidate_white"])
                assert row["score"] == expected
        matches[name] = {k: v for k, v in match.items() if k != "games"}
        shutil.copy2(RUN / f"matches-{name}.json", EVIDENCE / f"puzzle-pilot-20260906-{name}.json")
        (EVIDENCE / f"puzzle-pilot-20260906-{name}.pgn").write_text(
            "\n\n".join(r["pgn"] for r in match["games"]) + "\n", encoding="utf-8", newline="\n")
    validations = {}
    for recipe, folder in [("control", "puzzle-control-v1"), ("puzzle", "puzzle-mixed-v1")]:
        path = Path("candidates") / folder
        checks = [json.loads((RUN / f"{prefix}-{recipe}.json").read_text()) for prefix in ["validate", "validate-active"]]
        assert sum(c["legal_calls"] for c in checks) == 130 and checks[1]["policy_calls"] > 0
        assert all(c["sha256"] == sha256(path.with_suffix(".zip")) for c in checks)
        with zipfile.ZipFile(path.with_suffix(".zip")) as archive:
            assert archive.testzip() is None
            for name in archive.namelist():
                assert archive.read(name) == (path / name).read_bytes()
        validations[recipe] = checks
    summary = evaluation["summary"]
    before, after = [summary[name + ":production_agent"] for name in ["baseline", "puzzle"]]
    improving = (after["accepted"] > before["accepted"] and
                 after["blunders_200cp_both_budgets"] < before["blunders_200cp_both_budgets"])
    regressed_match = any(m["score"] < 0.5 for m in matches.values())
    decision = (
        "Retain as a provisional candidate for further comparison; the small production test improved, but raw-policy blunders increased and strength is not established."
        if improving and not regressed_match else
        "Do not promote on this pilot: the mixed evidence does not demonstrate a reliable improvement. Preserve the baseline and experimental checkpoint."
    )
    evidence = {"data": data, "audit": audit, "training": training, "evaluation": evaluation,
                "rollouts": rollouts, "matches": matches, "package_validations": validations,
                "decision": decision, "games_replayed": 16}
    evidence["read_only_validation"] = json.loads((RUN / "read-only-validation.json").read_text())
    assert all(value == "blocked" for value in evidence["read_only_validation"]["read_only_checks"].values())
    save_json(EVIDENCE / "puzzle-pilot-20260906-session.json", evidence)
    table = ["| Model | Evaluation | Accepted / 36 | Clear blunders / 27 CP-scored | Mean CP regret | Exact mate continuations / 9 |",
             "|---|---|---:|---:|---:|---:|"]
    for model in ["baseline", "control", "puzzle"]:
        for mode in ["raw_policy", "production_agent"]:
            row = summary[f"{model}:{mode}"]
            table.append(f"| {model} | {mode} | {row['accepted']} / {row['positions']} | {row['blunders_200cp_both_budgets']} / {row['cp_scored_positions']} | {row['mean_deep_regret_cp']:.1f} | {row['exact_continuations'].get('success', 0)} / 9 |")
    text = f"""# Verified puzzle and blunder pilot

**Decision: {decision}** This is a 320-position pilot, not a 10,000-puzzle run or a demonstrated Elo increase. The experimental upload package is `candidates/puzzle-mixed-v1.zip`; the ordinary-data control is `candidates/puzzle-control-v1.zip`.

## Data and verification

The supplied brief is preserved in `PUZZLE_TRAINING_PROMPT.md`. The importer streamed only 2,500 source CSV rows from the [CC0 Lichess puzzle database](https://database.lichess.org/#puzzles), parsed columns by name, applied the opponent's setup move before the solver move, and replayed every source continuation. The version, response headers, compressed-prefix hash and subset hash are in the acquisition manifest. Sampling used a bounded prefix and family-stratified ordering; it is not uniform over the database.

The final pilot contains 228 Lichess puzzles, 34 positions from actual earlier local games, 46 independently verified legal branches, and 12 constructed KQK examples kept entirely in training. Board validity is not asserted to prove historical reachability for constructed examples. Linked mistake and sound-alternative positions remain in the same source-game family. Not every attempted three-position family survived verification; no unverified third position is treated as tactic-free.

Counts: `{json.dumps(data['splits'])}`. Families: `{json.dumps(data['families'])}`. Colours: `{json.dumps(data['colours'])}`. Exact and colour-mirrored transpositions were deduplicated before splitting. 399,719 prior canonical player/value positions were excluded. Groups were split by source game/family; constructed near-neighbours are training-only. The original value dataset did not retain every source game ID, so cross-source game-level independence cannot be proved. Other related positions may remain.

Stockfish 19 (SHA `{data['teacher_sha256']}`), full strength, one thread and 32MB hash, separately analysed **every legal root move** with 80,000 and 320,000 total nodes per pass. Hash is cleared between passes. Actual nodes and legal principal variations are retained. Seventy-three short mates were proved exhaustively against all legal defences within one or three plies. A proof cutoff is unresolved. The other 247 records contain stable engine estimates; mate values are never silently converted into centipawns for their regret labels. Non-exact mate scores and unstable leading estimates were quarantined.

Independent replay checked {audit['legal_analysis_lines_replayed']:,} analysis lines and repeated all 73 exact proofs. Estimated acceptable alternatives lie within 70cp of the best at both budgets. A clear blunder loses at least 200cp at both budgets, from the same mover's perspective. Smaller inconsistent gaps remain uncertain; these thresholds do not prove game outcomes. Full histories are replayed where available; incomplete-history positions do not support repetition-dependent claims. No tablebases were used.

## Learning and actual execution

The existing 935–64–32–1 move-policy network receives a distribution over legal moves: uniform over every proved mating alternative for exact tasks, soft score-based targets for engine estimates. Motif tags, teacher scores, source IDs and solutions are excluded from inference inputs. The ordinary game-value network is untouched; task objectives are never relabelled as game victories. This is supervised learning, so no RL episode rewards, duplicate completion payments, critic or dense sacrifice/check bonuses were introduced.

Both models started from the frozen Magnus/Witty checkpoint. Each ran six epochs of 1,024 examples, 32-position batches, Adam and learning rate 0.0002. The control uses ordinary human-move imitation. The puzzle recipe uses 614 ordinary examples, 256 puzzle draws and 154 training-failure replay draws per epoch. Exposure is capped at four per position and 24 per puzzle family per epoch. Only training failures enter replay. Ordinary sampling retains the earlier phase-coverage data, but does not load the unsuccessful curriculum model's weights. Full-legal move counts differ, so the runs match update counts rather than claiming exactly equal floating-point work.

Checkpoint selection minimises 0.6 × broad-validation CE + 0.4 × puzzle-validation CE. Test positions were not encoded or examined for training or checkpoint selection. Actual training-loop times: `{json.dumps({k: v['seconds'] for k,v in training['recipes'].items()})}` seconds. The accepted-record verification total was {data['verification_seconds']:.2f} seconds; this excludes rejected candidates, import, deduplication and replay audit. No measured throughput is extrapolated into an automatic large download or paid run.

## Held-out findings

""" + "\n".join(table)
    text += """

These 36 held-out positions are a small grouped sample. The production improvement is one defensive position and one fewer clear blunder; the raw network's errors and false-positive attacks increased. This is mixed evidence, not proof of general tactical mastery or improved Elo. Some families contain only one or two test positions. Inference used the actual agent process at 4,000ms remaining clock, with its normal allocation; it did not receive four seconds per move. Search and runtime guards are unchanged, including bypassing neural preferences in check, low material phase and large evaluation imbalances. Both neural raw judgement and production choices are recorded; the teacher never chooses student moves.

Exact short-mate continuation results cover every defensive reply. Supplementary rollouts independently reverify later student choices against engine defence for up to three student decisions. Passing that short quality horizon remains a truncated game, not a solved longer puzzle or a win. Full conversion of general material advantages, opposition, fortress recognition, perpetual-check defence and long combinations has not been established. The known draw/underpromotion diagnostic set is reported separately and does not inflate the held-out score. Thirty readable training examples are in `PUZZLE_VERIFIED_EXAMPLES.md`.

## Full games and runtime

"""
    for name, match in matches.items():
        text += f"Against {name}: **{match['wins']}W/{match['draws']}D/{match['losses']}L**, eight games, pair standard error {match['pair_standard_error']}.\n\n"
    diag = Counter(r["model"] for r in evaluation["diagnostics"] if r["passed"])
    rollout_counts = Counter(f"{r['model']}:{r['mode']}:{r['status']}" for r in rollouts["episodes"])
    text += f"""Games used fixed colour-paired starts, 30+0.3 and a 400-ply cap. All 16 PGNs and their recorded results were replayed. These small matches do not calibrate a human or website rating. Known diagnostic passes: `{json.dumps(diag)}` out of 14 per model. Rollout outcomes: `{json.dumps(rollout_counts)}`.

Each extracted candidate ZIP passed 130 legal calls, including active-policy and optional-Alien checks. The runtime audit blocks file writes, networking and subprocess creation. The engine retains its own original search and trained weights; no verifier executable, teacher weights or evaluation lookup table ships. [Competition documentation](https://aichessathon.com/docs) permits training one's own network on labelled positions. Local validation is distinct from organiser Linux validation.

## Reproduction

Run from the project with its Python environment and fresh directories:

```powershell
python -m training.puzzle_data --out runs/puzzle-repeat/data --target 320
python -m scripts.audit_puzzle_data --data runs/puzzle-repeat/data
python -m training.puzzle_train --data runs/puzzle-repeat/data --out runs/puzzle-repeat/training
python -m scripts.puzzle_examples --data runs/puzzle-repeat/data --out runs/puzzle-repeat/examples.md
```

`configs/puzzle-pilot.json` freezes seed, architecture, budgets, learning rate and selection. `scripts/puzzle_session.py` records exact package, evaluation and paired-match commands; its dated outputs intentionally refuse overwriting prior evidence. The original bounded CSV subset and verification cache are retained locally. Subsequent source-database updates or engine timing differences may prevent byte-for-byte repetition; reuse the frozen dataset/checkpoints to reproduce assessments.

Evidence: `docs/evidence/puzzle-pilot-20260906-session.json`, two match JSONs/PGNs, and `runs/puzzle-pilot-20260906` for source subset, targets, quarantine, audit, RNG/optimizer checkpoints, training order, timings and all student attempts. Larger-scale training was not adopted automatically after this mixed pilot.
"""
    Path("docs/PUZZLE_PILOT_RESULTS.md").write_text(text, encoding="utf-8", newline="\n")
    print(json.dumps({"decision": decision, "matches": matches}, indent=2))


if __name__ == "__main__":
    main()
