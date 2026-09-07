"""Create a portable development archive, separate from the competition submission."""

import hashlib
import json
import zipfile
from pathlib import Path


def main():
    root = Path(__file__).resolve().parents[1]
    out = root.parent / "chess-agent-project.zip"
    files = [
        p
        for p in root.iterdir()
        if p.is_file()
        and p.suffix in {".md", ".py", ".json", ".toml", ".txt", ".csv", ".ps1"}
    ]
    files += [root / ".gitignore", root / "STARTER_LICENSE", root / "submission.zip"]
    files += [
        root / "candidates/alien-300k-hybrid-v2.zip",
        root / "candidates/alien-300k-hybrid-v2.manifest.json",
        root / "candidates/witty-300k-hybrid-v1.zip",
        root / "candidates/witty-300k-hybrid-v1.manifest.json",
        root / "candidates/mixed-classical-witty-v1.zip",
        root / "candidates/mixed-classical-witty-v1.manifest.json",
        root / "candidates/classical-witty-magnus-v1.zip",
        root / "candidates/classical-witty-magnus-v1.manifest.json",
        root / "candidates/carlsen-curriculum-v1.zip",
        root / "candidates/carlsen-curriculum-v1.manifest.json",
        root / "candidates/carlsen-curriculum-control-v1.zip",
        root / "candidates/carlsen-curriculum-control-v1.manifest.json",
        root / "candidates/puzzle-control-v1.zip",
        root / "candidates/puzzle-control-v1.manifest.json",
        root / "candidates/puzzle-mixed-v1.zip",
        root / "candidates/puzzle-mixed-v1.manifest.json",
        root / "candidates/fusion-hybrid-v1.zip",
        root / "candidates/fusion-hybrid-v1.manifest.json",
        root / "candidates/fusion-root-v1.zip",
        root / "candidates/fusion-root-v1.manifest.json",
    ]
    for directory in [
        "engine",
        "nn",
        "training",
        "scripts",
        "tests",
        "docs",
        "configs",
        "models",
        "harness",
        "baselines",
        "champions",
        "candidates/alien-300k-hybrid-v2",
        "candidates/witty-300k-hybrid-v1",
        "candidates/mixed-classical-witty-v1",
        "candidates/classical-witty-magnus-v1",
        "candidates/carlsen-curriculum-v1",
        "candidates/carlsen-curriculum-control-v1",
        "candidates/puzzle-control-v1",
        "candidates/puzzle-mixed-v1",
        "candidates/fusion-hybrid-v1",
        "candidates/fusion-root-v1",
        "data/lichess-50k",
        "runs/value-128",
        "runs/unattended-20260905-away/data-300000",
        "runs/unattended-20260905-away/value-300000-128",
    ]:
        files += [
            p
            for p in (root / directory).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        ]
    session = root / "runs/witty-style-20260906"
    files += [p for p in session.glob("*") if p.is_file() and p.suffix in {".json", ".log"}]
    files += [p for p in (session / "policy").glob("*") if p.suffix in {".json", ".npz"}]
    history = root / "data/witty_alien-history"
    if (history / "latest.json").exists():
        snapshot = history / json.loads((history / "latest.json").read_text())["export"]
        files += [
            history / "latest.json",
            history / "download-status.json",
            history / "archives.json",
        ]
        files += [
            snapshot / name
            for name in [
                "manifest.json",
                "style-analysis.json",
                "style-samples.manifest.json",
                "style-samples.jsonl",
            ]
        ]
    files = [p for p in files if p.is_file()]
    for name in ["fastchess-control-v1", "fastchess-static-v1", "fastchess-adaptive-v1", "threephase-pvs-v1",
                 "elite-case-seed-v1", "elite-teacher-control-v1",
                 *[f"elite-outcome-g{index:02}-v1" for index in range(1, 9)]]:
        folder = root / "candidates" / name
        files += [folder.with_suffix(".zip"), folder.with_suffix(".manifest.json")]
        files += [p for p in folder.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]
    for directory in ["runs/fastchess-pilot-20260906", "data/hikaru-gotham-pack",
                      "runs/threephase-pilot-20260906", "data/three-phase-pack",
                      "runs/elite-case-pilot-20260907", "data/elite-blitz-cases",
                      "runs/variants", "runs/unattended-20260905-away/candidate-100000-neural",
                      "runs/unattended-20260905-away/candidate-100000-hybrid",
                      "runs/unattended-20260905-away/candidate-300000-neural",
                      "runs/unattended-20260905-away/candidate-300000-hybrid"]:
        files += [p for p in (root / directory).rglob("*") if p.is_file() and "__pycache__" not in p.parts
                  and p.suffix in {".py", ".json", ".jsonl", ".npz", ".log", ".txt", ".md", ".csv", ".tsv", ".pgn"}]
    mixed = root / "runs/magnus-mixed-20260906"
    files += [p for p in mixed.rglob("*") if p.is_file() and p.suffix in {".json", ".jsonl", ".npz", ".log"}]
    curriculum = root / "runs/carlsen-curriculum-20260906"
    files += [p for p in curriculum.rglob("*") if p.is_file() and p.suffix in {".json", ".jsonl", ".npz", ".log"}]
    puzzle = root / "runs/puzzle-pilot-20260906"
    files += [p for p in puzzle.rglob("*") if p.is_file() and p.suffix in {".json", ".jsonl", ".npz", ".log"}]
    final = root / "runs/final-fusion-20260906"
    files += [p for p in final.rglob("*") if p.is_file() and p.suffix in {".json", ".npz", ".log"}]
    magnus_history = root / "data/magnuscarlsen-history"
    if (magnus_history / "latest.json").exists():
        magnus_export = magnus_history / json.loads((magnus_history / "latest.json").read_text())["export"]
        files += [magnus_history / name for name in ["latest.json", "archives.json", "download-status.json"]]
        files += [magnus_export / name for name in ["manifest.json", "style-analysis.json", "style-samples.manifest.json"]]
    temporary = root / "../../work/chess-agent-project.tmp.zip"
    selected = root.parent / "chessity-agent.zip"
    selected_metadata = root.parent / "chessity-agent-version.json"
    assert hashlib.sha256(selected.read_bytes()).hexdigest() == json.loads(selected_metadata.read_text())["sha256"]
    with zipfile.ZipFile(temporary, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for file in sorted(set(p for p in files if p.is_file())):
            archive.write(file, (Path("chess-agent") / file.relative_to(root)).as_posix())
        # Keep the README's ../chessity-agent.zip reference usable after extraction.
        for file in [selected, selected_metadata]:
            archive.write(file, file.name)
    with zipfile.ZipFile(temporary) as archive:
        assert archive.testzip() is None
    temporary.replace(out)
    print(
        f"{out}: {out.stat().st_size:,} bytes; includes source, 50k/300k data, player-policy samples/checkpoints, candidate runtimes and evidence; no external engine. Full raw player archives remain in the local project."
    )


if __name__ == "__main__":
    main()
