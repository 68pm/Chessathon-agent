"""Freeze an own-trained evaluator inside an otherwise identical verified runtime."""

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
    parser.add_argument('--model', type=Path, required=True)
    parser.add_argument('--value-blend', type=float, choices=(.25, 1.), default=1.)
    args = parser.parse_args()
    if Path(args.name).name != args.name:
        raise ValueError('Use a candidate name without path components.')
    base = args.base.resolve()
    target = ROOT / 'candidates' / args.name
    if target.exists():
        raise ValueError('Frozen candidates are immutable.')
    shutil.copytree(base, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(args.model, target / 'models/value.npz')
    config = json.loads((target / 'runtime.json').read_text(encoding='utf-8'))
    config.update(residual_value=True, value_blend=args.value_blend)
    (target / 'runtime.json').write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8', newline='\n')
    differences = [p.relative_to(base).as_posix() for p in base.rglob('*')
                   if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'
                   and p.read_bytes() != (target / p.relative_to(base)).read_bytes()]
    assert differences == ['runtime.json'], differences
    print(json.dumps(build(target, target.with_suffix('.zip')), indent=2))


if __name__ == '__main__':
    main()
