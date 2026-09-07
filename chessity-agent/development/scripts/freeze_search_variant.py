"""Freeze a one-file search experiment against an explicitly selected immutable base."""

import argparse
import json
import shutil
from pathlib import Path

from scripts.build_submission import build
from training.fastchess_data import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--name', required=True)
    args = parser.parse_args()
    if Path(args.name).name != args.name:
        raise ValueError('A candidate name, not a path, is required.')
    base = args.base.resolve()
    target = ROOT / 'candidates' / args.name
    if target.exists():
        raise ValueError('Frozen candidates are immutable.')
    shutil.copytree(base, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(ROOT / 'experiments/compiled_core.py', target / 'engine/compiled_core.py')
    differences = [p.relative_to(base).as_posix() for p in base.rglob('*')
                   if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'
                   and p.read_bytes() != (target / p.relative_to(base)).read_bytes()]
    assert differences == ['engine/compiled_core.py'], differences
    print(json.dumps(build(target, target.with_suffix('.zip')), indent=2))


if __name__ == '__main__':
    main()
