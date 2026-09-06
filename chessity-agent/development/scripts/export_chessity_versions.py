"""Prepare versioned public source/weight archives after final selection. Does not push."""

import argparse
import json
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

from scripts.alien_rating_ladder import save_json, sha256
from scripts.build_submission import build

VERSIONS = [
    ("champions/classical-v1", "Original classical engine", "historical; superseded timing implementation"),
    ("runs/variants/neural", "Original 50k neural evaluator", "experimental"),
    ("runs/variants/hybrid", "Original 50k classical/neural hybrid", "experimental"),
    ("runs/variants/style15", "Classical attacking-style experiment", "experimental"),
    ("runs/variants/style-aux", "Auxiliary style-target experiment", "experimental"),
    ("champions/classical-v2", "Classical engine with clock fixes", "preserved classical baseline"),
    ("runs/unattended-20260905-away/candidate-100000-neural", "100k neural evaluator", "experimental"),
    ("runs/unattended-20260905-away/candidate-100000-hybrid", "100k hybrid", "experimental"),
    ("runs/unattended-20260905-away/candidate-300000-neural", "300k neural evaluator", "experimental"),
    ("runs/unattended-20260905-away/candidate-300000-hybrid", "300k hybrid", "preserved value baseline"),
    ("candidates/alien-300k-hybrid", "Initial Alien Gambit hybrid", "historical forced-opening experiment"),
    ("candidates/alien-300k-hybrid-v2", "Revised Alien Gambit hybrid", "historical forced-opening experiment"),
    ("candidates/witty-300k-hybrid-v1", "Witty-trained 300k hybrid", "experimental forced-opening candidate"),
    ("candidates/mixed-classical-witty-v1", "Classical/Witty with optional Alien", "experimental"),
    ("candidates/classical-witty-magnus-v1", "Classical/Witty/Magnus policy", "preserved player-policy baseline"),
    ("candidates/carlsen-curriculum-control-v1", "Phase-pilot ordinary-data control", "control ablation"),
    ("candidates/carlsen-curriculum-v1", "Phase curriculum pilot", "not promoted"),
    ("candidates/puzzle-control-v1", "Puzzle-pilot ordinary-data control", "control ablation"),
    ("candidates/puzzle-mixed-v1", "Verified puzzle-trained player policy", "provisional; see mixed raw/search evidence"),
    ("candidates/fusion-hybrid-v1", "Full fusion with 300k leaf evaluator", "final comparison candidate"),
    ("candidates/fusion-root-v1", "Full fusion with bounded root value preference", "final comparison candidate"),
    ("candidates/fastchess-control-v1", "Fast-chess pilot matched broad-data control", "control ablation"),
    ("candidates/fastchess-static-v1", "Hikaru/Gotham verified policy with original clock controller", "clock ablation"),
    ("candidates/fastchess-adaptive-v1", "Hikaru/Gotham verified policy with adaptive 120+0.5 controller", "see measured pilot promotion decision"),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    selection = json.loads(args.selection.read_text())
    if selection.get("status") != "complete":
        raise ValueError("Complete final selection and rated tests before preparing publication")
    selected = (root / selection["selected_path"]).resolve()
    target = args.repo.resolve() / "chessity-agent"
    if target.exists():
        raise ValueError("Publication folder already exists; inspect before updating")
    if not (args.repo / ".git").is_dir():
        raise ValueError("Expected the existing repository checkout")
    target.mkdir()
    records = []
    for index, (relative, title, status) in enumerate(VERSIONS):
        source = root / relative
        if not (source / "agent.py").exists():
            raise ValueError(f"Missing preserved runtime: {relative}")
        version = "v1" if index == 0 else f"v1.{index}"
        destination = target / "versions" / version
        destination.mkdir(parents=True)
        archive = destination / f"chessity-agent-{version}.zip"
        original_archive = source.with_suffix(".zip")
        if original_archive.exists():
            shutil.copy2(original_archive, archive)
        else:
            build(source, archive)
        formatting_differences = []
        with zipfile.ZipFile(archive) as zipped:
            assert zipped.testzip() is None and "agent.py" in zipped.namelist()
            for name in zipped.namelist():
                path = Path(name)
                assert not path.is_absolute() and ".." not in path.parts
                assert path.suffix in {".py", ".json", ".npz"}
                archived_bytes = zipped.read(name)
                local_bytes = (source / path).read_bytes()
                if archived_bytes != local_bytes:
                    # Preserve the original archive when only JSON formatting changed locally.
                    # Extracted public source must still be byte-for-byte the archived source.
                    assert path.suffix == ".json" and json.loads(archived_bytes) == json.loads(local_bytes), name
                    formatting_differences.append(name)
            zipped.extractall(destination / "source")
        recommended = source.resolve() == selected
        subprocess.run([sys.executable, "-m", "scripts.validate_package", "--zip", str(archive),
                        "--clock-ms", "1000", "--calls", "3", "--out", str(destination / "read-only-check.json")],
                       cwd=root, check=True, capture_output=True, text=True)
        check = json.loads((destination / "read-only-check.json").read_text())
        assert check["sha256"] == sha256(archive)
        assert all(value == "blocked" for value in check["read_only_checks"].values())
        record = dict(version=version, name="chessity-agent", title=title, status=status,
                      recommended=recommended, source_version=relative, sha256=sha256(archive),
                      zip_bytes=archive.stat().st_size,
                      archive_json_formatting_differs_from_local_folder=formatting_differences,
                      read_only_smoke_calls=check["legal_calls"],
                      archive=f"versions/{version}/{archive.name}")
        save_json(destination / "version.json", record)
        (destination / "README.md").write_text(
            f"# chessity-agent {version}\n\n{title}. Status: {status}.\n\n"
            f"Competition ZIP: `{archive.name}`. SHA-256: `{record['sha256']}`. "
            "Readable source and trained weights extracted from that exact ZIP are in `source/`. "
            "Historical versions are retained for development comparison; their presence is not a recommendation or an Elo claim.\n",
            encoding="utf-8", newline="\n")
        records.append(record)
    recommended = [r for r in records if r["recommended"]]
    assert len(recommended) == 1
    chosen = recommended[0]
    latest = target / "latest"
    latest.mkdir()
    shutil.copy2(target / chosen["archive"], latest / "chessity-agent.zip")
    assert sha256(latest / "chessity-agent.zip") == selection["selected_zip_sha256"]
    save_json(latest / "version.json", chosen)
    # Publish human-readable results and own development code, not downloaded player histories.
    for directory in ["engine", "nn", "training", "scripts", "configs", "tests", "harness"]:
        for source in (root / directory).rglob("*"):
            if source.is_file() and source.suffix in {".py", ".json"} and "__pycache__" not in source.parts:
                destination = target / "development" / source.relative_to(root)
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
    for name in ["STARTER_LICENSE", "requirements-dev.txt", "ENGINE_SPEC.md", "agent.py", "runtime.json"]:
        shutil.copy2(root / name, target / "development" / name)
    reports = target / "reports"
    reports.mkdir()
    for name in ["MAGNUS_MIXED_SESSION.md", "CARLSEN_CURRICULUM_RESULTS.md", "PUZZLE_PILOT_RESULTS.md",
                 "PUZZLE_VERIFIED_EXAMPLES.md", "FINAL_FUSION_RESULTS.md", "COMBINED_AGENT_TEST.md",
                 "WITTY_TRAINING_SESSION.md", "ALIEN_RATING_LADDER.md", "FASTCHESS_OPENING_GRAPH.md", "FASTCHESS_PILOT_RESULTS.md"]:
        shutil.copy2(root / "docs" / name, reports / name)
    public_evidence = reports / "evidence"
    public_evidence.mkdir()
    for name in ["fastchess-loss-audit.json", "fastchess-opening-depth-coverage.json",
                 "fastchess-source-audit.json", "fastchess-verified-data-manifest.json",
                 "fastchess-training-exposure-audit.json"]:
        shutil.copy2(root / "docs/evidence" / name, public_evidence / name)
    for prefix in ["final-fusion-20260906", "fastchess-pilot-20260906"]:
        for stage in ["comparison", "rated"]:
            for suffix in [".json", ".pgn"]:
                name = f"{prefix}-{stage}{suffix}"
                shutil.copy2(root / "docs/evidence" / name, public_evidence / name)
    save_json(target / "versions.json", {"recommended": chosen["version"], "versions": records,
                                         "publication_order": "Preserved development stages; controls and rejected experiments explicitly labelled."})
    readme = ["# chessity-agent", "", f"Best tested package in this session: **{chosen['version']}** — {chosen['title']}.", "",
              "[Download the competition ZIP](latest/chessity-agent.zip). Upload this ZIP, not the repository source archive.", "",
              "[The latest fast-chess report](reports/FASTCHESS_PILOT_RESULTS.md) contains the promotion decision and fresh 1700/2000/2200 tests. The preceding fusion report preserves the earlier six-agent comparison and 2000/2200 tests. These final sessions use 120+0.5. Opponent settings are not an official human or website rating.", "",
              "## Read-only runtime and repository access", "",
              "The final package was tested with file creation, deletion, renaming and directory creation blocked. Runtime inference needs no file writes, network access or subprocesses. Training tools are separate and intentionally write checkpoints. GitHub public visitors can read and download this repository; editing it requires repository write permission. No collaborator or public write grants are added by this publication.", "",
              "## Versions", "", "| Version | Build | Status |", "|---|---|---|"]
    for record in records:
        readme.append(f"| [{record['version']}]({record['archive']}) | {record['title']} | {'Best tested in this session' if record['recommended'] else record['status']} |")
    readme += ["", "Source and weights for each archive are retained beside it. Neural weights were trained locally; no third-party chess engine or pretrained chess network ships in the agent ZIPs. Offline verifier and opponent engines are development tools only. Code was developed with AI assistance. Downloaded player histories and external engine executables are not published here.", "",
               "The development scripts retain their original local project layout and references. Full training datasets remain in the local project; this repository alone is not a byte-for-byte training reproduction bundle.", ""]
    (target / "README.md").write_text("\n".join(readme), encoding="utf-8", newline="\n")
    root_readme = args.repo / "README.md"
    existing = root_readme.read_text(encoding="utf-8")
    root_readme.write_text(existing.rstrip() + "\n\n## chessity-agent releases\n\n"
                           f"[Download the best tested agent ({chosen['version']})](chessity-agent/latest/chessity-agent.zip) · "
                           "[All versioned builds and results](chessity-agent/README.md)\n\n"
                           "Agents are tested for read-only runtime operation. Public visitors have read access; repository edits require write permission.\n",
                           encoding="utf-8", newline="\n")
    print(json.dumps({"versions": len(records), "recommended": chosen, "destination": str(target)}, indent=2))


if __name__ == "__main__":
    main()
