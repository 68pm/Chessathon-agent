"""Safely preserve the user-supplied factual game pack before offline verification."""

import argparse
import json
import zipfile
from pathlib import Path

from scripts.alien_rating_ladder import save_json, sha256

FILES = {"AGENT_PROMPT.md", "README.md", "games.csv", "games.pgn", "manifest.json",
         "opening-reference.tsv", "player-decisions.jsonl"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError("Preserve existing import; use a fresh destination")
    with zipfile.ZipFile(args.zip) as archive:
        if set(archive.namelist()) != FILES or len(archive.infolist()) != len(FILES):
            raise ValueError("Unexpected pack members")
        if sum(item.file_size for item in archive.infolist()) > 80_000_000:
            raise ValueError("Unexpected expanded pack size")
        if archive.testzip() is not None:
            raise ValueError("Corrupt archive")
        args.out.mkdir(parents=True)
        for name in sorted(FILES):
            (args.out / name).write_bytes(archive.read(name))
    report = {"archive": str(args.zip.resolve()), "archive_sha256": sha256(args.zip),
              "files": {name: {"bytes": (args.out / name).stat().st_size,
                               "sha256": sha256(args.out / name)} for name in sorted(FILES)},
              "scope": "User-supplied data. All source chess and labels require project verification; no bundled code executed."}
    save_json(args.out / "import.json", report)
    Path("docs/HIKARU_GOTHAM_TRAINING_PROMPT.md").write_bytes((args.out / "AGENT_PROMPT.md").read_bytes())
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
