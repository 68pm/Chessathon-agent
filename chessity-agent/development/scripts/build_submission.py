"""Allowlist-only, deterministic zip. Import dependency and size audit before writing."""

import argparse
import ast
import hashlib
import json
import sys
import zipfile
from pathlib import Path


def build(root, out):
    config = json.loads((root / "runtime.json").read_text())
    files = [root / "agent.py", root / "runtime.json"]
    if config.get("elementary_tables"):
        files += sorted((root / "tables").glob("*.rtbw"))
        files += sorted((root / "tables").glob("*.rtbz"))
        files += [root / "tables/SOURCE.txt", root / "tables/manifest.json"]
    files += sorted((root / "engine").glob("*.py"))
    if config["mode"] == "classical" and not config.get("root_value") and not config.get("residual_value"):
        excluded = {"neural.py"} if config.get("player_policy") else {"features.py", "neural.py"}
        files = [f for f in files if f.name not in excluded]
    else:
        files += [root / "models" / "value.npz"]
    if not config.get("root_value"):
        files = [f for f in files if f.name != "fusion.py"]
    if config.get("player_policy"):
        files += [root / "models" / "player-policy.npz"]
    else:
        files = [f for f in files if f.name != "player_policy.py"]
    allowed = set(sys.stdlib_module_names) | {"chess", "numpy", "engine"}
    if config.get("compiled_search"):
        allowed.add("numba")
    for f in files:
        if f.suffix == ".py":
            tree = ast.parse(f.read_text())
            for node in ast.walk(tree):
                names = (
                    [a.name for a in node.names]
                    if isinstance(node, ast.Import)
                    else [node.module]
                    if isinstance(node, ast.ImportFrom) and node.module
                    else []
                )
                for name in names:
                    if name.split(".")[0] not in allowed:
                        raise ValueError(f"Forbidden import {name} in {f}")
    size = sum(f.stat().st_size for f in files)
    if size >= 50_000_000:
        raise ValueError("Submission must be under 50 MB uncompressed")
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for f in sorted(files):
            name = f.relative_to(root).as_posix()
            info = zipfile.ZipInfo(name, date_time=(2026, 9, 5, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, f.read_bytes(), compresslevel=9)
    report = {
        "sha256": hashlib.sha256(out.read_bytes()).hexdigest(),
        "zip_bytes": out.stat().st_size,
        "uncompressed_bytes": size,
        "files": [f.relative_to(root).as_posix() for f in files],
        "mode": config,
        "runtime_dependencies": ["chess==1.11.2"]
        + (
            []
            if config["mode"] == "classical" and not config.get("player_policy") and not config.get("compiled_search")
            else ["numpy==2.5.2"]
        ) + (["numba==0.67.0"] if config.get("compiled_search") else []),
    }
    out.with_suffix(".manifest.json").write_text(json.dumps(report, indent=2))
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=Path("."))
    p.add_argument("--out", type=Path, default=Path("submission.zip"))
    a = p.parse_args()
    print(json.dumps(build(a.root, a.out), indent=2))


if __name__ == "__main__":
    main()
