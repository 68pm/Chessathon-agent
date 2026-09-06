"""Replay the finished fixed benchmark and publish the Magnus mixture evidence."""

import csv
import io
import json
import zipfile
from collections import Counter
from pathlib import Path

import chess.pgn

from engine.openings import alien_move
from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import CANDIDATE, PREVIOUS, manifest, summary

RUN = Path("runs/magnus-mixed-20260906")
EVIDENCE = Path("docs/evidence")


def audit_games(report, partial=False):
    assert len(report["schedule"]) == 92
    if partial:
        assert report["status"] in {"running", "complete"}
        assert {g["id"] for g in report["games"]} <= {g["id"] for g in report["schedule"]}
    else:
        assert report["status"] == "complete" and len(report["games"]) == 92
        assert {g["id"] for g in report["games"]} == {g["id"] for g in report["schedule"]}
    protocol = {j["id"]: j for j in report["schedule"]}
    opportunities = choices = replayed = 0
    for row in report["games"]:
        assert all(row[key] == value for key, value in protocol[row["id"]].items())
        assert row["score"] is not None
        game = chess.pgn.read_game(io.StringIO(row["pgn"]))
        assert game is not None and not game.errors
        board = game.board()
        initial = chess.Board()
        for uci in row["opening"]:
            initial.push_uci(uci)
        assert board.fen() == initial.fen()
        for move in game.mainline_moves():
            if board.turn == row["white"]:
                hint = alien_move(board)
                if hint and hint.uci() == "g5f7":
                    opportunities += 1
                    choices += move.uci() == "g5f7"
            assert move in board.legal_moves
            board.push(move)
        if row["termination"] == "ply_cap":
            assert row["score"] == 0.5
        elif row["termination"] != "flag":
            outcome = board.outcome(claim_draw=True)
            assert outcome and outcome.termination.name.lower() == row["termination"]
            expected = 0.5 if outcome.winner is None else float(outcome.winner == row["white"])
            assert row["score"] == expected
        white_score = row["score"] if row["white"] else 1 - row["score"]
        assert game.headers["Result"] == {1: "1-0", 0.5: "1/2-1/2", 0: "0-1"}[white_score]
        assert game.headers["TimeControl"] == "30+0.3"
        if "final_fen" in row:
            assert board.fen() == row["final_fen"]
        replayed += 1
    return {
        "games_replayed": replayed,
        "results_verified": True,
        "alien_sacrifice_opportunities": opportunities,
        "alien_sacrifices_chosen": choices,
        "terminations": dict(Counter(r["termination"] for r in report["games"])),
    }


def main():
    import argparse

    p = argparse.ArgumentParser()
    p.add_argument("--partial-audit", action="store_true")
    a = p.parse_args()
    report = json.loads((RUN / "benchmark/results.json").read_text())
    if a.partial_audit:
        print(json.dumps(audit_games(report, partial=True), indent=2))
        return
    audit = audit_games(report)
    assert manifest(CANDIDATE) == report["candidate_files"]
    assert manifest(PREVIOUS) == report["previous_files"]
    archive = CANDIDATE.with_suffix(".zip")
    assert sha256(archive) == report["candidate_zip_sha256"]
    with zipfile.ZipFile(archive) as package:
        assert package.testzip() is None
        for name in package.namelist():
            assert package.read(name) == (CANDIDATE / name).read_bytes()
        assert not any(name.endswith((".exe", ".dll", ".nnue")) for name in package.namelist())
    assert (
        sha256("submission.zip")
        == "b2d40403213ef339686106b4999484b7192d3ebf6477e29c17d62e63e5160d77"
    )
    assert (
        sha256(PREVIOUS.with_suffix(".zip"))
        == "ee0f02da9613786001689673e6d68157f5965e5820efc4feea67a8bec5112e95"
    )
    for name in report["candidate_files"]:
        if name != "models/player-policy.npz":
            assert (CANDIDATE / name).read_bytes() == (PREVIOUS / name).read_bytes()
    policy = json.loads((RUN / "policy/evaluation.json").read_text())
    config = json.loads((RUN / "policy/config.json").read_text())
    assert config["initial_policy_sha256"] == sha256(PREVIOUS / "models/player-policy.npz")
    assert sha256(CANDIDATE / "models/player-policy.npz") == policy["weights_sha256"]
    assert policy["weights_sha256"] != config["initial_policy_sha256"]
    validations = [
        json.loads((RUN / path).read_text())
        for path in ["package-validation.json", "active-validation.json"]
    ]
    assert sum(v["legal_calls"] for v in validations) == 130
    assert all(
        v["sha256"] == report["candidate_zip_sha256"] and v["selective_alien_verified"]
        for v in validations
    )
    assert validations[1]["policy_calls"] > 0
    mixture = json.loads((RUN / "mixture/manifest.json").read_text())
    assert sha256(RUN / "mixture/samples.jsonl") == mixture["sha256"] == config["samples_sha256"]
    comparison = json.loads((RUN / "policy-comparison.json").read_text())
    for model in comparison["models"].values():
        for player in ["magnuscarlsen", "witty_alien"]:
            model[player]["limitation"] = (
                "Same held-out whole-game split and exact positions for both models. Magnus samples have no forcing-move priority; Witty samples prioritise forcing moves. Imitation accuracy is not tactical accuracy or Elo; related positions may cross splits."
            )
    history = Path("data/magnuscarlsen-history")
    status = json.loads((history / "download-status.json").read_text())
    export = history / status["export"]
    analysis = json.loads((export / "style-analysis.json").read_text())
    metrics = json.loads((RUN / "policy/metrics.json").read_text())["epochs"]
    best = min(metrics, key=lambda r: r["validation"]["cross_entropy"])
    results = summary(report["games"])
    proof = {
        "training": json.loads((RUN / "training-session.json").read_text()),
        "data": mixture,
        "data_audit": json.loads((RUN / "data-audit.json").read_text()),
        "history_analysis": analysis,
        "policy_config": config,
        "policy_metrics": metrics,
        "policy_evaluation": policy,
        "policy_comparison": comparison,
        "package_validation": validations,
        "benchmark_audit": audit,
        "summary": results,
        "candidate_zip_sha256": sha256(archive),
        "candidate_bytes": archive.stat().st_size,
        "runtime_code_identical_to_previous": True,
        "new_neural_weights": True,
        "previous_packages_preserved": True,
        "unit_tests_passed": 49,
        "source_commit_before_matches": "e21812a",
    }
    EVIDENCE.mkdir(exist_ok=True)
    save_json(EVIDENCE / "magnus-mixed-20260906-session.json", proof)
    save_json(EVIDENCE / "magnus-mixed-20260906-games.json", report)
    for family in ["madchess", "stockfish", "previous"]:
        rows = [r for r in report["games"] if r["family"] == family]
        (EVIDENCE / f"magnus-mixed-20260906-{family}.pgn").write_text(
            "\n\n".join(r["pgn"] for r in rows) + "\n"
        )
    highest = [
        r
        for r in report["games"]
        if r["family"] in {"madchess", "stockfish"}
        and r["score"] == 1
        and r["termination"] == "checkmate"
        and r["elo"] == results["highest_checkmate_win_by_family"][r["family"]]
    ]
    (EVIDENCE / "magnus-mixed-20260906-highest-wins.pgn").write_text(
        "\n\n".join(r["pgn"] for r in highest) + "\n"
    )
    table = ["| Opponent | Wins | Draws | Losses |", "|---|---:|---:|---:|"]
    for label, group in results["by_opponent"].items():
        table.append(
            f"| {label} | {group.get('wins', 0)} | {group.get('draws', 0)} | {group.get('losses', 0)} |"
        )
    previous = results["by_opponent"]["previous:None"]
    narrative = (
        "The new candidate won more than it lost in the small direct comparison, but this does not establish a reliable strength improvement."
        if previous.get("wins", 0) > previous.get("losses", 0)
        else "The direct comparison did not demonstrate a strength improvement over the previous agent. Keep both versions; the new neural policy is a better move imitator on these samples, but is not established as the stronger chess agent."
    )
    text = f"""# Classical + Witty Alien + Magnus Carlsen

Candidate: `candidates/classical-witty-magnus-v1.zip` ({archive.stat().st_size:,} bytes).
SHA256: `{sha256(archive)}`. Use `Play-Magnus-Mix.ps1` for local play.

Highest checkmate victories: **MadChess {results["highest_checkmate_win_by_family"]["madchess"]}** and **Stockfish {results["highest_checkmate_win_by_family"]["stockfish"]}** on their nominal strength settings.
These settings and a highest individual win are not an official Elo for this agent.
{narrative}

## Games downloaded and training

Collected all **{status["unique_games"]:,}** completed games exposed by the named account's public index, in **{status["archives_listed"]} months** and **{status["parts"]} parts** (maximum 50 records each), with no missing PGNs. This covers the supplied MagnusCarlsen account, not every game Magnus has played elsewhere. Private, deleted and unexposed games are outside the download.
The original JSON and PGNs remain under `{history}`. The combined PGN is `{export}/all-available-games.pgn`.

Analysis retained **{analysis["counts"]["games"]:,} standard games** and **{analysis["counts"]["player_moves"]:,} Magnus decisions**; {analysis["counts"]["variant_games_skipped"]} variant games were retained in the archive and excluded from standard-chess training. Every monthly/part checksum matched; 100 sampled Magnus labels were traced to their real source games.

The new policy uses **{mixture["positions"]:,} positions**: 50,000 Witty and {mixture["by_player"]["magnuscarlsen"]:,} Magnus examples, after removing 66 overlapping positions. Magnus sampling includes quiet decisions without forcing-move priority; Witty retains its previous attacking-biased sample. All prior Witty splits are preserved, no exact normalized FEN is retained twice, and source games never cross splits. Related positions may still remain across splits.

The 935–64–32–1 NumPy policy has 62,017 parameters. It was initialised from the Witty-trained policy and fitted on both datasets with equal per-position weight, learning rate 0.0003, seed 20260906, up to four alternative legal moves per label. Validation stopped training after {len(metrics)} epochs; epoch {best["epoch"]} was selected by validation cross-entropy ({best["validation"]["cross_entropy"]:.6f}). Splits: {policy["splits"]["train"]:,} training, {policy["splits"]["validation"]:,} validation, {policy["splits"]["test"]:,} test positions. Training is supervised move imitation, not self-play or 300,000 new games.

Classical has no learned dataset/weights to average: its evaluation and search remain the decision-making component. The newly fitted neural policy supplies a bounded 10-centipawn root preference; optional Alien preparation supplies up to 15 more. Search considers all legal moves, and proven mate scores remain unchanged. The earlier 300k value network is preserved separately and is not loaded in this package. All runtime code/configuration is byte-identical to the previous combined candidate; the policy weights changed.

## Held-out move agreement

Each cell uses the same 1,000 held-out positions for both models; these are raw network choices before search, not engine accuracy percentages or Elo.

| Player samples | Previous top 1 | New top 1 | Previous top 3 | New top 3 |
|---|---:|---:|---:|---:|
"""
    for player in ["magnuscarlsen", "witty_alien"]:
        old, new = [comparison["models"][key][player] for key in ["previous_witty", "magnus_witty"]]
        text += f"| {player} | {old['top1']:.1%} | {new['top1']:.1%} | {old['top3']:.1%} | {new['top3']:.1%} |\n"
    text += "\n## Fixed match results\n\n" + "\n".join(table)
    text += f"""

All 92 games used 30 seconds plus 0.3 seconds per move per side, at most two simultaneous games, with fresh processes. Each MadChess rung used both colours from the starting position and after `1.e4 c6 2.d4 d5`. Stockfish 1700 and the previous combined candidate each used six colour-paired openings. The full schedule and candidate hashes were frozen before outcomes, with no retries chosen to chase a win.

All 92 PGNs were replayed and their results checked. Terminations: `{json.dumps(audit["terminations"])}`. Alien sacrifice opportunities in these games: {audit["alien_sacrifice_opportunities"]}; sacrifices chosen: {audit["alien_sacrifices_chosen"]}. The package check independently confirmed that its optional preparation can decline `6.Nxf7`, choosing `6.N5f3` in the standard test position.

## Verification and limits

49 unit tests passed; the extracted competition ZIP passed 130 legal-move calls, including 18 active-policy calls in the 30-call longer-clock audit. Both package audits verified optional Alien integration, memory below 2 GB, and no runtime writes, network access or subprocesses. Local Windows tests do not replace the organiser's Linux validation. No external engine, third-party engine weights or game archive is included in the candidate.

The prior combined ZIP and selected classical `submission.zip` are preserved. A disk-space failure occurred before fitting; temporary derived feature/shard caches were removed, the failure log was retained, and training then completed. Training samples, source archives, model checkpoints and results remain available; feature caches can be regenerated for resume.

MadChess settings are not calibrated to a verified human rating pool. Stockfish's handicap calibration also depends on its test conditions; 30+0.3 games here are not a Chess.com, FIDE or competition rating. Four games per MadChess level and twelve against each other opponent leave substantial uncertainty. Better imitation does not establish stronger tactical search or better endgame play.

## Reproducibility and sources

Full evidence: `docs/evidence/magnus-mixed-20260906-session.json`, `docs/evidence/magnus-mixed-20260906-games.json`, and the three opponent-family PGNs. Highest winning games: `docs/evidence/magnus-mixed-20260906-highest-wins.pgn`.

The user's previous confirmation of written Chess.com authorisation and the present instruction to download/train on this account are the recorded authorisation basis. The grant text was not independently inspected. Collection used the documented public API serially with caching and delays.

- [MagnusCarlsen account](https://www.chess.com/member/magnuscarlsen)
- [Chess.com public API](https://www.chess.com/news/view/published-data-api)
- [MadChess strength calibration FAQ](https://www.madchess.net/the-madchess-uci_limitstrength-algorithm/limit-strength-faq/)
- [Stockfish UCI options](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-Protocol-and-Stockfish-Commands.html)
"""
    Path("docs/MAGNUS_MIXED_SESSION.md").write_text(text, encoding="utf-8")
    block = f"""## Magnus + Witty + Classical candidate

`candidates/classical-witty-magnus-v1.zip` adds a newly fitted neural move policy
trained on {mixture["positions"]:,} positions from both players, using the unchanged
classical search and optional Alien preparation. Downloaded 9,694 available Magnus
games in 194 parts. In the fixed 92-game test, the highest checkmate victories were
MadChess {results["highest_checkmate_win_by_family"]["madchess"]} and Stockfish
{results["highest_checkmate_win_by_family"]["stockfish"]} nominal settings. Against
the previous combined agent it scored {previous.get("wins", 0)}W/{previous.get("draws", 0)}D/{previous.get("losses", 0)}L.
{narrative}
See `docs/MAGNUS_MIXED_SESSION.md` for training, every rung, PGNs and limitations.
Use `Play-Magnus-Mix.ps1` for local play. Previous packages remain available.
"""
    for filename in ["README.md", "MODEL_CARD.md", "CHANGELOG.md"]:
        path = Path(filename)
        current = path.read_text(encoding="utf-8")
        begin, end = "<!-- MAGNUS_SESSION_START -->", "<!-- MAGNUS_SESSION_END -->"
        if begin in current:
            start, finish = current.index(begin), current.index(end) + len(end)
            current = current[:start] + current[finish:].lstrip("\n")
        title, remainder = current.split("\n", 1)
        path.write_text(
            title + "\n\n" + begin + "\n" + block + "\n" + end + "\n\n" + remainder.lstrip("\n"),
            encoding="utf-8",
        )
    ledger = Path("EXPERIMENTS.csv")
    with ledger.open(newline="") as stream:
        reader = csv.DictReader(stream)
        fields, records = reader.fieldnames, list(reader)
    records = [r for r in records if not r["experiment_id"].startswith("magnus-mixed-20260906-")]
    for family in ["madchess", "stockfish", "previous"]:
        rows = [r for r in report["games"] if r["family"] == family]
        records.append(
            {
                "experiment_id": "magnus-mixed-20260906-" + family,
                "date": "2026-09-06",
                "git_commit": "e21812a",
                "champion_commit": "a7c01a7",
                "change": "New jointly fitted Magnus/Witty policy with unchanged classical search and selective Alien hints",
                "config": "candidates/classical-witty-magnus-v1/runtime.json",
                "seed": 20260906,
                "dataset_hash": mixture["sha256"],
                "games": len(rows),
                "time_control": "30+0.3",
                "wins": sum(r["score"] == 1 for r in rows),
                "draws": sum(r["score"] == 0.5 for r in rows),
                "losses": sum(r["score"] == 0 for r in rows),
                "score": sum(r["score"] for r in rows) / len(rows),
                "model_bytes": (CANDIDATE / "models/player-policy.npz").stat().st_size,
                "zip_bytes": archive.stat().st_size,
                "decision": "experimental_candidate",
                "notes": "Fixed protocol, all PGNs replayed. Highest checkmate settings "
                + str(results["highest_checkmate_win_by_family"])
                + ". Not an official Elo or established strength gain. See docs/MAGNUS_MIXED_SESSION.md.",
            }
        )
    with ledger.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
