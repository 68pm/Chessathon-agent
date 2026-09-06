"""Extract and checksum the supplied research pack without executing bundled code."""

import hashlib
import json
import stat
import zipfile
from pathlib import Path, PurePosixPath


def main():
    root = Path(__file__).resolve().parents[1]
    archive = Path("C:/Users/disea/Downloads/Chess-Three-Phase-Research-and-Training-Pack.zip")
    target = root / "data/three-phase-pack"
    expected = "367e2fa1e215cee1c2d12182013d3e8f036d5f46f8c3e7c5b2f4813df3e1d719"
    actual = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert actual == expected
    if target.exists():
        raise ValueError("Preserve existing extracted pack")
    with zipfile.ZipFile(archive) as source:
        assert source.testzip() is None
        assert sum(row.file_size for row in source.infolist()) < 100_000_000
        seen, rows = set(), []
        for row in source.infolist():
            name = PurePosixPath(row.filename)
            assert name.parts[0] == "Chess-Three-Phase-Pack" and len(name.parts) > 1
            assert not name.is_absolute() and ".." not in name.parts and "\\" not in row.filename
            assert not stat.S_ISLNK(row.external_attr >> 16)
            relative = Path(*name.parts[1:])
            assert relative.as_posix().casefold() not in seen
            seen.add(relative.as_posix().casefold())
            assert relative.suffix in {".md", ".json", ".jsonl", ".pgn", ".txt", ".csv", ".tsv", ".py"}
            rows.append((row, relative))
        target.mkdir(parents=True)
        for row, relative in rows:
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read(row))
    verified = 0
    for line in (target / "SHA256SUMS.txt").read_text().splitlines():
        checksum, name = line.split(maxsplit=1)
        relative = PurePosixPath(name.lstrip("*"))
        assert not relative.is_absolute() and ".." not in relative.parts
        assert hashlib.sha256((target / Path(*relative.parts)).read_bytes()).hexdigest() == checksum, name
        verified += 1
    report = dict(archive=str(archive), archive_sha256=actual, extracted_files=len(rows),
                  supplied_checksums_verified=verified, code_execution="None during extraction")
    (root / "docs/evidence/threephase-pack-import.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
