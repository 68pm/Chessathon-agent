"""Audit the completed supplied-pack pilot and apply its predeclared promotion rule."""

import json
import math
import re
import shutil
import statistics
import subprocess
import sys
import zipfile
from collections import Counter

import chess
import chess.pgn

from scripts.alien_rating_ladder import save_json, sha256
from scripts.export_chessity_versions import VERSIONS
from scripts.fastchess_matches import CANDIDATE, CONTROL, FAILURES, STATIC, score_summary
from scripts.magnus_benchmark import manifest
from scripts.rating_benchmark import summarize as rating_summary
from training.fastchess_data import CONFIG, ROOT, RUN


def audit_game(row, config):
    import io

    game = chess.pgn.read_game(io.StringIO(row["pgn"]))
    assert game and not game.errors and game.headers["TimeControl"] == "120+0.5"
    board = chess.Board()
    for uci in row["opening"]:
        board.push_uci(uci)
    assert game.board().fen() == board.fen()
    board = game.board()
    clocks = {True: float(config["base_ms"]), False: float(config["base_ms"])}
    pgn_moves = list(game.mainline_moves())
    limits = {record["ply"]: record for record in row["uci_limits"]}
    assert len(pgn_moves) == len(row["moves"])
    for move, info in zip(pgn_moves, row["moves"], strict=True):
        assert move.uci() == info["uci"] and move in board.legal_moves and board.fen() == info["fen"]
        side = board.turn
        if board.ply() in limits:
            limit = limits[board.ply()]
            assert abs(limit["white_clock"] * 1000 - clocks[True]) < 0.001
            assert abs(limit["black_clock"] * 1000 - clocks[False]) < 0.001
        assert side == info["white"] and abs(clocks[side] - info["clock_before_ms"]) < 0.001
        assert info["elapsed_ms"] >= 0 and info["elapsed_ms"] < clocks[side]
        clocks[side] += 500 - info["elapsed_ms"]
        assert abs(clocks[side] - info["clock_after_ms"]) < 0.001
        board.push(move)
    assert board.fen() == row["final_fen"]
    for limit in row["uci_limits"]:
        assert limit["white_inc"] == limit["black_inc"] == 0.5
    white_score = row["score"] if row["candidate_white"] else 1 - row["score"]
    assert game.headers["Result"] == {1: "1-0", 0.5: "1/2-1/2", 0: "0-1"}[white_score]
    if row["termination"] not in FAILURES | {"ply_cap"}:
        outcome = board.outcome(claim_draw=True)
        assert outcome and outcome.termination.name.lower() == row["termination"]
        assert white_score == (0.5 if outcome.winner is None else float(outcome.winner))


def promotion(comparison, rated, evaluation):
    table = score_summary(comparison["games"])
    reasons = []
    if table["previous_best"]["pair_bootstrap_95"][0] <= 0.5:
        reasons.append("Paired-opening lower 95% score bound did not exceed 50% against the preserved best.")
    for name in ["matched_control", "static_clock"]:
        if table[name]["score"] < 0.5:
            reasons.append(f"Candidate scored below 50% against {name}.")
    if any(r["termination"] in FAILURES for r in comparison["games"] + rated["games"]):
        reasons.append("A reliability failure occurred in the fixed match set.")
    actual = [r for r in evaluation["rows"] if r["model"] == "candidate" and r["mode"] in {"production", "opening_continuation"}]
    if any(not r["assessment"]["legal"] or r["seconds"] * 1000 >= r["clock_ms"] for r in actual):
        reasons.append("A candidate legality/clock overrun occurred in the position assessment.")
    return not reasons, reasons


def main():
    config = json.loads(CONFIG.read_text())
    session = json.loads((RUN / "session.json").read_text())
    assert session["status"] == "complete"
    comparison = json.loads((RUN / "comparison/results.json").read_text())
    rated = json.loads((RUN / "rated/results.json").read_text())
    evaluation = json.loads((RUN / "evaluation/results.json").read_text())
    loss_audit = json.loads((RUN / "loss-audit.json").read_text())
    assert loss_audit["status"] == "complete"
    for report in [comparison, rated, evaluation]:
        assert report["status"] == "complete"
    for report, expected in [(comparison, 2 * sum(config["comparison_pairs"].values())),
                             (rated, 2 * config["rated_pairs_per_setting"] * len(config["rated_settings"]))]:
        assert len(report["games"]) == len(report["schedule"]) == expected
        schedule = {r["id"]: r for r in report["schedule"]}
        for row in report["games"]:
            assert all(row[k] == v for k, v in schedule[row["id"]].items())
            audit_game(row, config)
        assert report["files"] == {relative: manifest(ROOT / relative) for relative in report["files"]}
    data = json.loads((RUN / "data/manifest.json").read_text())
    assert sha256(RUN / "data/verified.jsonl") == data["verified_sha256"]
    train = json.loads((RUN / "training/report.json").read_text())
    assert train["status"] == "complete"
    chosen_epochs = {name: min(recipe["epochs"], key=lambda row: row["selection_score"])["epoch"]
                     for name, recipe in train["recipes"].items()}
    assert sha256(CANDIDATE / "models/player-policy.npz") == sha256(STATIC / "models/player-policy.npz") == train["recipes"]["fastchess"]["best_sha256"]
    assert sha256(CONTROL / "models/player-policy.npz") == train["recipes"]["control"]["best_sha256"]
    accepted, reasons = promotion(comparison, rated, evaluation)
    previous = json.loads((ROOT / "runs/final-fusion-20260906/selection.json").read_text())
    selected = CANDIDATE if accepted else ROOT / previous["selected_path"]
    relative = selected.relative_to(ROOT).as_posix()
    index = [r[0] for r in VERSIONS].index(relative)
    version = "v1" if index == 0 else f"v1.{index}"
    archive = selected.with_suffix(".zip")
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        for name in zipped.namelist():
            assert zipped.read(name) == (selected / name).read_bytes()
    probe = RUN / "validate-selected-real-clock.json"
    subprocess.run([sys.executable, "-m", "scripts.validate_package", "--zip", str(archive),
                    "--clock-ms", "120000", "--calls", "2", "--out", str(probe)], cwd=ROOT, check=True)
    check = json.loads(probe.read_text())
    assert check["sha256"] == sha256(archive) and all(v == "blocked" for v in check["read_only_checks"].values())
    candidate_levels = score_summary(rated["games"])
    old_evidence = json.loads((ROOT / "docs/evidence/final-fusion-20260906-session.json").read_text())
    selected_levels = candidate_levels if accepted else old_evidence["levels"]
    highest_new = max((r["elo"] for r in rated["games"] if r["score"] == 1), default=None)
    old_rated = json.loads((ROOT / "runs/final-fusion-20260906/rated/results.json").read_text())
    nominal = rating_summary([dict(agent=name, pair=f"{r['elo']}:{r['pair']}",
                                   score=r["score"], opponent_elo=r["elo"])
                              for name, report in [("new_candidate", rated), ("preserved_best", old_rated)]
                              for r in report["games"]])
    selection = dict(status="complete", selected_name=selected.name, selected_path=relative,
                     selected_zip_sha256=sha256(archive), public_version=version, candidate_promoted=accepted,
                     promotion_reasons=reasons, previous_selection=previous,
                     candidate_rated_results=candidate_levels, selected_rated_results=selected_levels,
                     highest_new_candidate_winning_setting=highest_new,
                     nominal_rating_estimates=nominal,
                     time_control="120+0.5", read_only_validation=check)
    save_json(RUN / "selection.json", selection)
    shutil.copy2(archive, ROOT.parent / "chessity-agent.zip")
    save_json(ROOT.parent / "chessity-agent-version.json", dict(name="chessity-agent", version=version,
        source_candidate=selected.name, sha256=sha256(archive), time_control="120+0.5",
        results=selected_levels, new_candidate_results=candidate_levels, read_only_checks=check["read_only_checks"]))
    evidence = ROOT / "docs/evidence"
    save_json(evidence / "fastchess-loss-audit.json", loss_audit)
    depth_coverage = json.loads((RUN / "evaluation/opening-depth-coverage.json").read_text())
    save_json(evidence / "fastchess-opening-depth-coverage.json", depth_coverage)
    for label, report in [("session", selection), ("comparison", comparison), ("rated", rated), ("evaluation", evaluation)]:
        save_json(evidence / f"fastchess-pilot-20260906-{label}.json", report)
        if "games" in report:
            (evidence / f"fastchess-pilot-20260906-{label}.pgn").write_text(
                "\n\n".join(r["pgn"] for r in report["games"]) + "\n", encoding="utf-8", newline="\n")
    comparison_summary = score_summary(comparison["games"])
    load = [r["host_cpu_busy_fraction"] for r in comparison["games"] + rated["games"]
            if r.get("host_cpu_busy_fraction") is not None]
    load_note = (f"Host-wide average CPU use across individual games ranged from {min(load):.1%} to {max(load):.1%}, "
                 f"with median {statistics.median(load):.1%}. These counters include all applications and initialization; "
                 "they do not establish isolated-core conditions or attribute timing failures to a particular process. "
                 "Other applications were observed consuming substantial CPU during data verification. "
                 "Node-budget verification stayed fixed; wall-clock match performance remains specific to the recorded local conditions.") if load else "Host CPU-load counters were unavailable."
    lines = ["# Hikaru/Gotham verified fast-chess pilot", "",
        f"**Selected upload: chessity-agent {version}, `{selected.name}`.** " + ("The new candidate passed the predeclared local promotion checks." if accepted else "The new candidate did not meet the promotion rule; the preserved best remains the recommended upload."), "",
        f"Selected ZIP SHA-256: `{sha256(archive)}`. The ZIP in the parent outputs directory is the exact selected archive. No competition upload was performed.", "",
        "## Data and architecture", "",
        "The supplied pack was audited by replaying all 2,135 games, 93,786 named-player decisions and recorded post-move clocks, plus 556 opening reference lines. It contains 1,063 Hikaru and 1,072 GothamChess games; Hikaru is the GM source and Levy Rozman the IM source. None of these games uses 120+0.5. Their clocks remain observational metadata, not a learned time-allocation target.", "",
        f"The verified pilot contains {data['human_positions']['train']} new human-game training positions, {data['human_positions']['validation']} validation and {data['human_positions']['test']} test positions, {sum(data['graph_nodes'].values())} train-only opening decisions, and {data['error_pairs']} independently verified punishment positions paired with observed training blunders. {data['observed_human_moves_accepted']} of the {sum(data['human_positions'].values())} human choices met the verifier's acceptable-move criterion; the other {data['observed_human_moves_replaced']} use corrected soft alternatives. Counts describe this selected pilot, not all player games.", "",
        "Stockfish 19 served only as an offline teacher, with one thread, 32MB hash and full-legal MultiPV at 80k and 320k nodes, cleared hash between passes. Estimates must agree under the existing puzzle verifier; unstable or non-exact mate scores are quarantined. Short forced mates are exact only when the exhaustive solver proves them. Scores use the root side's perspective. Drawing defence is never labelled as a won game.", "",
        f"The existing 935–64–32–1 policy starts from the preserved puzzle-trained Carlsen/Witty policy. Both control and candidate receive {config['epochs']} epochs of {config['examples_per_epoch']} examples, batch size {config['batch_size']} and learning rate {config['learning_rate']}. Candidate exposure is approximately 60% broad Carlsen/Witty phase coverage, 25% verified bundle/graph and 15% verified training errors/puzzle replay. Exposure caps are four per position and 24 per related family per epoch. Validation, not test results, selects checkpoints with weights 0.60 broad, 0.25 new validation and 0.15 puzzle validation. Legal-move counts vary, so equal update counts do not imply identical FLOPs.", "",
        f"Validation selected control epoch {chosen_epochs['control']} and candidate epoch {chosen_epochs['fastchess']}. Thus the complete training runs have matched update budgets, while the selected checkpoints represent different numbers of updates. The saved training-order audit confirmed training-only replay; the largest observed per-board exposure in a candidate epoch was two, and the largest recorded-family exposure was 24. Earlier source-game identification limitations still apply.", "",
        "The new runtime uses the original classical node evaluator, a bounded 10cp policy preference and the same optional 15cp Alien hint in all three new builds. The Alien sacrifice remains optional. Existing guards disable learned root preferences in check, late endgames, large static imbalances and tiny budgets; raw-policy gains there do not establish a production endgame improvement. Previously trained 300k value and fusion variants remain preserved and were included in the preceding six-agent comparison; incompatible network weights were not averaged. Broad phase concepts and verified move targets reuse the Carlsen and puzzle modules without importing the rejected phase-curriculum checkpoint.", "",
        "## Opening and clock changes", "",
        f"Verified own-side graph counts: `{json.dumps(data['graph_nodes'])}`. It stores actual-state keys, separate full history, multiple sound choices, verified opponent replies where resolved, sampled training-game reply frequencies, factual pawn/file structure, original study prompts and counterexamples. It is a partial curriculum, not a complete connected repertoire. See `FASTCHESS_OPENING_GRAPH.md`. The graph is training-only: no teacher move/evaluation lookup ships. Book-on/off for this graph is therefore inapplicable; training-board recall is reported separately from unseen-board and continuation tasks. No videos or transcripts were converted into training labels.", "",
        "The adaptive controller retains a legal move, returns promptly for a single legal reply, reserves at least 30ms when available, modestly increases the allocation in check, and adjusts its soft deadline after completed iterations when choices or scores are unstable. A hard wall-clock stop remains. Board features and the value interface are unchanged. The static-clock ablation shares the candidate's exact policy weights. Equal-node tests disable clock adaptation to study judgement separately from practical speed.", "",
        "The actual referee and UCI transport passed fractional-increment tests: 120,000ms initially, 500ms only after a legal on-time move, and `winc 500 binc 500`. A late move cannot be rescued by increment. Production position probes include 10,000ms, 2,500ms and 800ms remaining clocks; these are remaining game clocks, not fixed per-move budgets.", "",
        "## Fresh paired matches at 120+0.5", "", "| Opponent | W | D | L | Score | Paired bootstrap 95% interval |", "|---|---:|---:|---:|---:|---|"]
    for name, group in {**comparison_summary, **candidate_levels}.items():
        lines.append(f"| {name} | {group['wins']} | {group['draws']} | {group['losses']} | {group['score']:.1%} | {group['pair_bootstrap_95']} |")
    lines += ["", f"Highest Stockfish handicap setting the **new candidate** defeated in this test: **{highest_new if highest_new is not None else 'none at the tested settings'}**. These are nominal engine settings, not measured Chess.com, FIDE or competition Elo. A highest individual win is not a stable rating. The earlier selected baseline's 2000/2200 results remain in `FINAL_FUSION_RESULTS.md`.", "",
        f"All {len(comparison['games']) + len(rated['games'])} new game PGNs, move clocks, increments, start positions, results and frozen source hashes passed replay checks. Terminations: `{json.dumps(dict(Counter(r['termination'] for r in comparison['games'] + rated['games'])))}`. The matched pairs and promotion rule were declared before outcomes. Intervals resample opening pairs; their small sample and any identical observations can understate uncertainty. Even promotion is provisional local evidence, not proof of strongest-possible or GM-standard play.", "",
        load_note, "",
        "Promotion decision: " + ("passed the declared rule." if accepted else " ".join(reasons)), "",
        "## Conditional rating estimate", "",
        "To answer the user's estimate request, the existing fractional-score Elo fit is applied to the actual rated games. This is conditional on Stockfish's nominal handicap numbers behaving like Elo anchors. It is a descriptive performance estimate on that local scale, not a human, website or official competition rating. It does not enter the promotion rule. The broad band combines a colour-pair bootstrap with a Wilson score envelope, rounded outwards; it cannot cover calibration, hardware or model error.", "",
        "| Build | Nominal handicap-scale estimate | Broad descriptive band |", "|---|---:|---|"]
    for name, stats in nominal.items():
        estimate = stats["nominal_handicap_scale_estimate"]
        low, high = stats["approximate_uncertainty_envelope"]
        band = f"{math.floor(low / 100) * 100 if low is not None else 'unbounded'} to {math.ceil(high / 100) * 100 if high is not None else 'unbounded'}"
        lines.append(f"| {name} | {round(estimate) if estimate is not None else 'no finite estimate'} | {band} |")
    lines += ["", "## Position quality and practical cost", "", "| Model / mode / clock | Accepted | CP-scored | 200cp blunders | Mean deep regret | Median ms | p95 ms |", "|---|---:|---:|---:|---:|---:|---:|---:|"]
    for name, group in evaluation["summary"].items():
        regret = group["mean_deep_regret_cp"]
        lines.append(f"| {name} | {group['accepted']}/{group['positions']} | {group['cp_positions']} | {group['blunders_200cp_both_budgets']} | {regret if regret is not None else 'n/a'} | {group['median_ms']:.2f} | {group['p95_ms']:.2f} |")
    raw = {name: evaluation["summary"][f"{name}:raw_policy:None"]
           for name in ["previous_best", "matched_control", "candidate"]}
    node_moves = {name: {r["id"]: r["uci"] for r in evaluation["rows"]
                        if r["model"] == name and r["mode"] == "equal_nodes"}
                  for name in raw}
    changed = sum(move != node_moves["previous_best"][key] for key, move in node_moves["candidate"].items())
    recall = {r["model"]: r for r in evaluation["graph_recall"]}
    lines += ["", f"Raw-policy recognition was {raw['candidate']['accepted']}/{raw['candidate']['positions']} acceptable choices for the candidate, "
              f"versus {raw['previous_best']['accepted']} for the preserved best and {raw['matched_control']['accepted']} for the matched control. "
              f"Their verified 200cp error counts were {raw['candidate']['blunders_200cp_both_budgets']}, "
              f"{raw['previous_best']['blunders_200cp_both_budgets']} and {raw['matched_control']['blunders_200cp_both_budgets']}, respectively. "
              "Small count differences on this selected test set are descriptive, not proof of a general tactical improvement.", "",
              f"At the fixed node budget the candidate changed {changed} of {len(node_moves['candidate'])} moves relative to the preserved best. "
              "The probe loads each saved policy and preserves its bounded root preference; classical search and existing policy guards can dominate the decision. "
              "The three timed tests reuse the same 48 boards, so their 144 calls are not 144 independent positions. "
              "Sequential timing and throughput measurements also reflect changing host load and should not be interpreted as a causal speed gain from the training recipe.", "",
              f"Training-graph recall was {recall['candidate']['accepted']}/{recall['candidate']['positions']} for the candidate, "
              f"{recall['previous_best']['accepted']} for the preserved best and {recall['matched_control']['accepted']} for control. "
              "This measures recall of training boards; the separate continuation tasks and full games are the relevant checks of play beyond those examples.", ""]
    lines += ["", "### Existing opening hint on/off", "",
              "The permitted handwritten Alien preference was also compared on/off on known opening positions, at equal nodes and at a 4,000ms remaining-clock input. The latter calls get_move directly and excludes wire overhead. This diagnostic does not count as held-out neural recognition or full-game strength evidence; the new verified graph remains offline training material.", "",
              "| Mode / hint | Accepted | Verified 200cp errors | Prepared moves followed |", "|---|---:|---:|---:|"]
    for name, group in evaluation["book_ablation"]["summary"].items():
        lines.append(f"| {name} | {group['accepted']}/{group['positions']} | {group['blunders']} | {group['prepared_moves_followed']} |")
    lines += ["", "The evidence JSON retains phase/task breakdowns and every move assessment. The six-ply `plan_unseen_continuation` task tests an unseen continuation, without claiming it exceeds the stored repertoire's depth. A separate `after_deepest_stored_line` diagnostic selects a verified test-game position strictly beyond the deepest stored graph decision for each family where one is available; missing families are explicit in `evaluation/opening-depth-coverage.json`. These cases reuse the held-out pool and are not independent extra games. Root recognition and short continuation quality do not prove full middlegame conversion or endgame mastery. Post-test loss analysis samples up to 48 positions; unresolved mate/unstable scores are retained as unresolved. These losses were never fed back into training.", "",
        "## Leakage, reliability and reproducibility", "",
        f"Post-test diagnosis examined {loss_audit['attempted_positions']} sampled positions from losses: "
        f"{len(loss_audit['rows'])} received stable verified assessments and {len(loss_audit['unresolved'])} remained unresolved. "
        f"Among the resolved samples, {loss_audit['sampled_verified_blunders']} met the two-budget 200cp blunder criterion. "
        "This is a selected sample, not a count of every mistake or a causal explanation of the losses. "
        "The complete diagnosis is in `evidence/fastchess-loss-audit.json`; family depth coverage is in "
        "`evidence/fastchess-opening-depth-coverage.json`.", "",
        "Benchmark wins and losses never update the network. All tested weights stay fixed; outcomes affect selection "
        "and the descriptive rating estimate only. The current learner uses verified move targets and corrective "
        "examples, not reinforcement-learning win rewards. Any future outcome training needs separate training games "
        "and fresh evaluation games.", "",
        "Whole supplied games retain their split. Exact/mirrored boards shared across splits, earlier player/value/puzzle boards, and recognized earlier source games are excluded from the fresh assessment pool. Related punishment branches keep the source training family. The train-only graph avoids earlier held-out boards. The original 300k dataset lacks recoverable source-game IDs, so related-position, opening-family and unknown teacher-data overlap cannot be ruled out completely. This limitation is separate from the verified zero exact cross-split duplicates.", "",
        f"The selected ZIP passed another read-only probe at a 120,000ms input clock: import {check['init_ms']:.2f}ms, observed peak memory {check['peak_working_set_bytes']} bytes. File creation, deletion, directory creation and renaming were blocked, along with network/process operations. It contains readable own source and locally trained weights, with no external engine or teacher lookup. These are Windows local audits, not the organiser's Linux validation.", "",
        "`configs/fastchess-pilot.json`, `configs/fastchess-openings.json`, `training/fastchess_data.py`, `training/fastchess_train.py` and the `scripts/fastchess_*` modules define the experiment. The session records source hashes, verification cache, exact sampled orders, checkpoints, validation metrics, read-only probes, position assessments and complete games under `runs/fastchess-pilot-20260906`. Original sources and unsuccessful checkpoints are preserved. No paid compute was used.", "",
        "Primary resource rules: [AI Chessathon](https://aichessathon.com/docs), [python-chess engine interface](https://python-chess.readthedocs.io/en/latest/engine.html), [CC0 opening-name reference](https://github.com/lichess-org/chess-openings). Opening names are classifications, not best-move evidence. The player pack has its own provenance; it is not represented as entirely CC0.", ""]
    (ROOT / "docs/FASTCHESS_PILOT_RESULTS.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    note = f"\n<!-- FASTCHESS_SESSION_START -->\n## Current selected upload: chessity-agent {version}\n\nUse `../chessity-agent.zip` ({selected.name}). The Hikaru/Gotham pilot {'passed' if accepted else 'did not pass'} the promotion gate. All new matches use **120+0.5**; read-only runtime checks passed. See `docs/FASTCHESS_PILOT_RESULTS.md` for the candidate's exact results and the preserved baseline comparison. No independent human/site Elo is claimed.\n<!-- FASTCHESS_SESSION_END -->\n"
    for name in ["README.md", "MODEL_CARD.md"]:
        path = ROOT / name
        text = path.read_text(encoding="utf-8")
        text = re.sub(r"\n<!-- FINAL_FUSION_SESSION_START -->.*?<!-- FINAL_FUSION_SESSION_END -->\n", "\nEarlier fusion selection and its dated results are preserved in `docs/FINAL_FUSION_RESULTS.md`.\n", text, flags=re.S)
        text = re.sub(r"\n<!-- FASTCHESS_SESSION_START -->.*?<!-- FASTCHESS_SESSION_END -->\n", "\n", text, flags=re.S)
        first, rest = text.split("\n", 1)
        path.write_text(first + "\n" + note + rest, encoding="utf-8", newline="\n")
    print(json.dumps(selection, indent=2))


if __name__ == "__main__":
    main()
