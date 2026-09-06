"""Replay final competition-clock evidence and expose the exact selected upload ZIP."""

import io
import json
import math
import shutil
import zipfile
from collections import Counter

import chess
import chess.pgn

from scripts.alien_rating_ladder import save_json, sha256
from scripts.export_chessity_versions import VERSIONS
from scripts.final_fusion_benchmark import AGENTS, ROOT, RUN
from scripts.magnus_benchmark import manifest


def audit_game(row, rated):
    game = chess.pgn.read_game(io.StringIO(row["pgn"]))
    assert game and not game.errors and game.headers["TimeControl"] == "120+0.5"
    board = game.board()
    expected = chess.Board()
    for uci in row["opening"]:
        expected.push_uci(uci)
    assert board.fen() == expected.fen()
    for move in game.mainline_moves():
        assert move in board.legal_moves
        board.push(move)
    assert row["termination"] not in {"illegal", "crash", "init", "invalid", "both_failed"}
    white_score = (row["score"] if row["white"] else 1 - row["score"]) if rated else row["white_score"]
    assert game.headers["Result"] == {1: "1-0", 0.5: "1/2-1/2", 0: "0-1"}[white_score]
    if row["termination"] not in {"flag", "ply_cap"}:
        outcome = board.outcome(claim_draw=True)
        assert outcome and outcome.termination.name.lower() == row["termination"]
        assert white_score == (0.5 if outcome.winner is None else float(outcome.winner))
    return board


def main():
    selection = json.loads((RUN / "selection.json").read_text())
    assert selection["status"] == "complete"
    comparison = json.loads((RUN / "comparison/results.json").read_text())
    rated = json.loads((RUN / "rated/results.json").read_text())
    assert comparison["status"] == rated["status"] == "complete"
    for report, count, is_rated in [(comparison, 30, False), (rated, 24, True)]:
        assert len(report["games"]) == count
        assert (report["config"]["base_ms"], report["config"]["increment_ms"], report["config"]["ply_cap"]) == (120000, 500, 600)
        scheduled = {r["id"]: r for r in report["schedule"]}
        assert set(scheduled) == {r["id"] for r in report["games"]}
        for row in report["games"]:
            assert all(row[key] == value for key, value in scheduled[row["id"]].items())
            audit_game(row, is_rated)
    assert comparison["files"] == {name: manifest(path) for name, path in AGENTS.items()}
    selected = AGENTS[selection["selected_name"]]
    assert rated["files"] == manifest(selected)
    archive = selected.with_suffix(".zip")
    assert sha256(archive) == selection["selected_zip_sha256"]
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        for name in zipped.namelist():
            assert zipped.read(name) == (selected / name).read_bytes()
    check = json.loads((RUN / "validate-selected-real-clock.json").read_text())
    assert check["sha256"] == sha256(archive) and check["clock_ms"] == 120000
    assert all(value == "blocked" for value in check["read_only_checks"].values())
    index = [item[0] for item in VERSIONS].index(selection["selected_path"])
    version = "v1" if index == 0 else f"v1.{index}"
    levels = {}
    for elo in [2000, 2200]:
        rows = [r for r in rated["games"] if r["elo"] == elo]
        assert len(rows) == 12 and sum(r["white"] for r in rows) == 6
        pairs = [sum(r["score"] for r in rows if r["pair"] == pair) / 2 for pair in range(6)]
        mean = sum(pairs) / len(pairs)
        levels[elo] = dict(games=12, wins=sum(r["score"] == 1 for r in rows),
                           draws=sum(r["score"] == 0.5 for r in rows), losses=sum(r["score"] == 0 for r in rows),
                           score=mean, pair_standard_error=math.sqrt(sum((v - mean) ** 2 for v in pairs) / 5 / 6),
                           terminations=dict(Counter(r["termination"] for r in rows)))
    winning_levels = [r["elo"] for r in rated["games"] if r["score"] == 1]
    highest = max(winning_levels) if winning_levels else None
    evidence = {"selection": selection, "public_version": version, "levels": levels,
                "highest_winning_setting_in_final_test": highest,
                "read_only_validation": check, "games_replayed": 54,
                "unit_test_log": (RUN / "unit-tests.log").read_text(),
                "rating_limit": "Stockfish nominal handicap settings; no established human/site/competition Elo. Individual wins and highest total in a small selection tournament do not prove a stable rating or strongest possible engine."}
    output = ROOT.parent / "chessity-agent.zip"
    shutil.copy2(archive, output)
    save_json(ROOT.parent / "chessity-agent-version.json", {
        "name": "chessity-agent", "version": version, "source_candidate": selection["selected_name"],
        "sha256": sha256(output), "time_control": "120+0.5", "results": levels,
        "read_only_checks": check["read_only_checks"]})
    evidence_dir = ROOT / "docs/evidence"
    save_json(evidence_dir / "final-fusion-20260906-session.json", evidence)
    for name, report in [("comparison", comparison), ("rated", rated)]:
        save_json(evidence_dir / f"final-fusion-20260906-{name}.json", report)
        (evidence_dir / f"final-fusion-20260906-{name}.pgn").write_text(
            "\n\n".join(r["pgn"] for r in report["games"]) + "\n", encoding="utf-8", newline="\n")
    table = ["| Agent | W | D | L | Points / 10 |", "|---|---:|---:|---:|---:|"]
    for name in selection["ranking"]:
        row = selection["standings"][name]
        table.append(f"| {name} | {row['wins']} | {row['draws']} | {row['losses']} | {row['points']} |")
    text = f"""# Chessity agent: final combination and competition-clock test

**Best observed comparison score: `{selection['selected_name']}`, published as chessity-agent {version}.** The exact selected competition ZIP is `chessity-agent.zip` in the parent outputs folder. SHA-256: `{sha256(output)}`. Selection followed the predeclared score/tie rule; this small local test does not prove that it is the strongest possible agent.

## What was combined

The two new fusion candidates combine the existing original 300k-position value model (775–128–32–1) and the newer move-policy model (935–64–32–1) with the original classical search. The policy retains Witty/Magnus imitation and the verified puzzle pilot's ordinary phase-coverage, puzzle and failure-replay training. These are two compatible learned components used by one agent; incompatible weight matrices were not averaged or presented as a single newly trained architecture. Some accumulated data was used for validation/testing rather than training; raw player histories were sampled rather than every move being fitted.

`fusion-hybrid` evaluates search leaves using 80% classical and 20% learned value, with a bounded 10cp policy preference. `fusion-root` retains classical node evaluation and adds at most 5cp from the learned child-position value to the 10cp player/puzzle preference, under the existing root guards. Child values are negated back to the root mover's perspective; terminal mate/draw outcomes are handled explicitly. The latter avoids neural evaluation at every search leaf. Both retain the optional 15cp Alien opening hint. The engine can decline the sacrifice. Speculative aggression never receives an unconditional training reward.

The failed curriculum checkpoint was preserved rather than averaged into a new model. Its useful phase-sampling data had already been incorporated into the puzzle experiment. Historical baselines and all experimental variants remain versioned. If a preserved baseline tops the final comparison, it is selected on the evidence rather than automatically replacing it with the newest file.

## Fixed comparison at 120+0.5

The user confirmed **120 seconds per side plus 0.5 seconds per move**. All 54 games in this final session used that clock, a 600-ply cap, both colours, and at most two simultaneous games. The earlier 30+0.3 experiments remain historical evidence and did not substitute for these fresh games.

Six agents played one colour-reversed opening pair per opponent pairing: 30 games total and ten per agent. Pair openings and the exact tie preference were frozen before outcomes in `configs/final-fusion.json`. The highest total selected the candidate for the separate rated tests. The score advantage is provisional; ten games per agent is a small screening sample.

""" + "\n".join(table)
    text += "\n\n## Fresh rated opponents\n\n| Stockfish setting | W | D | L | Games |\n|---|---:|---:|---:|---:|\n"
    for elo, row in levels.items():
        text += f"| {elo} | {row['wins']} | {row['draws']} | {row['losses']} | 12 |\n"
    text += f"""
Highest opponent setting defeated in these final tests: **{highest if highest is not None else 'none; no win at 2000 or 2200'}**. The opponent was Stockfish 19 with `UCI_LimitStrength=true`, the stated `UCI_Elo`, one thread, 64MB hash and 20ms move overhead. It is a locally handicapped engine, not a verified human or Chess.com bot rating. The official [Stockfish UCI documentation](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-Protocol-and-Stockfish-Commands.html) describes these options. No independent Elo rating is inferred from a highest individual win.

Each level used six opening pairs, with colours reversed. Pair standard errors were `{json.dumps({k: v['pair_standard_error'] for k,v in levels.items()})}`; a zero empirical standard error from identical outcomes does not mean zero uncertainty. All recorded PGNs were legally replayed and the result, opening, time-control and frozen-file checks passed. Terminations: `{json.dumps({k: v['terminations'] for k,v in levels.items()})}`.

## Read-only runtime and resources

The new entrypoints disable bytecode caching. Package probes reject file creation, deletion, directory creation and renaming, plus other filesystem mutation events, networking and subprocesses. The selected ZIP passed again at a 120,000ms remaining-clock input. Import time was {check['init_ms']:.2f}ms; observed peak working set was {check['peak_working_set_bytes']} bytes. These are local measurements, separate from organiser Linux validation. Training code writes checkpoints outside the runtime package. Runtime transposition/history updates occur only in memory.

The agent ZIP contains readable Python and the selected original trained weights. No external engine implementation, executable, teacher weights, downloaded game archive or teacher evaluation lookup database is included. The competition permits training a team's own network on engine-labelled positions; see its [documentation](https://aichessathon.com/docs). Authorship and data provenance are described in the earlier player and puzzle reports. All source was developed with AI coding assistance.

## Reproduction and evidence

`scripts/final_fusion_session.py` records the exact build, package, test, validation, comparison and rated-test commands. `configs/final-fusion.json` records the final clock, candidates, data-model paths, bounded fusion constants and selection rule. Dated paths refuse overwriting evidence; use new output paths for another experiment. Opponent randomisation and wall-clock search timing can vary across runs.

`docs/evidence/final-fusion-20260906-session.json`, the comparison/rated JSONs and PGNs preserve the results. `runs/final-fusion-20260906` contains per-game records, clocks for rated games, package probes, source hashes and all controller logs. The original value/policy training datasets and checkpoints remain in the local project. No competition upload was performed by these tests; the user receives the verified ZIP to submit.
"""
    (ROOT / "docs/FINAL_FUSION_RESULTS.md").write_text(text, encoding="utf-8", newline="\n")
    note = f"""\n<!-- FINAL_FUSION_SESSION_START -->
## chessity-agent {version}: selected upload

The final comparison selected `{selection['selected_name']}`. Use `../chessity-agent.zip`
for the competition upload. All final games used **120+0.5**. Stockfish 2000:
{levels[2000]['wins']}W/{levels[2000]['draws']}D/{levels[2000]['losses']}L; Stockfish 2200:
{levels[2200]['wins']}W/{levels[2200]['draws']}D/{levels[2200]['losses']}L.
Read-only runtime checks passed. See `docs/FINAL_FUSION_RESULTS.md` for selection,
earlier-clock limitations and complete evidence. The default historical `submission.zip`
and previous candidates remain archived versions; the explicitly named selected upload
is the package identified by this final report.
<!-- FINAL_FUSION_SESSION_END -->\n"""
    for name in ["README.md", "MODEL_CARD.md"]:
        path = ROOT / name
        original = path.read_text(encoding="utf-8")
        if "<!-- FINAL_FUSION_SESSION_START -->" not in original:
            first, rest = original.split("\n", 1)
            path.write_text(first + "\n" + note + rest, encoding="utf-8", newline="\n")
    print(json.dumps({"version": version, "selected": selection['selected_name'], "levels": levels,
                      "highest_winning_setting": highest, "zip": str(output)}, indent=2))


if __name__ == "__main__":
    main()
