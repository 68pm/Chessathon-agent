"""Freeze our compiled experiment as a self-contained, source-only candidate."""

import argparse
import json
import shutil
from pathlib import Path

from scripts.build_submission import build
from training.fastchess_data import ROOT


def create(name, conversion=False, reductions=False, model=None, blend=0.0, tables=False,
           table_directory=None, table_max_pieces=3):
    baseline = ROOT / 'candidates/classical-witty-magnus-v1'
    candidate = ROOT / 'candidates' / name
    if candidate.exists():
        raise ValueError('Frozen candidates are immutable; choose a new name.')
    (candidate / 'engine').mkdir(parents=True)
    (candidate / 'models').mkdir()
    for name in ['__init__.py', 'time_manager.py', 'openings.py', 'player_policy.py', 'features.py', 'evaluation.py']:
        shutil.copy2(baseline / 'engine' / name, candidate / 'engine' / name)
    for name in ['compiled_core.py', 'compiled_driver.py']:
        shutil.copy2(ROOT / 'experiments' / name, candidate / 'engine' / name)
    if tables:
        shutil.copy2(ROOT / 'experiments/elementary_endgames.py', candidate / 'engine/elementary_endgames.py')
        shutil.copytree(table_directory or ROOT / 'data/elementary-syzygy', candidate / 'tables')
    shutil.copy2(ROOT / 'experiments/compiled_agent.py', candidate / 'agent.py')
    shutil.copy2(baseline / 'models/player-policy.npz', candidate / 'models/player-policy.npz')
    if model:
        shutil.copy2(model, candidate / 'models/value.npz')
    config = json.loads((baseline / 'runtime.json').read_text())
    config.update(compiled_search=True, conversion=conversion, reductions=reductions,
                  residual_value=bool(model), value_blend=blend, elementary_tables=tables)
    if tables and table_max_pieces != 3:
        config['table_max_pieces'] = table_max_pieces
    (candidate / 'runtime.json').write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8', newline='\n')
    report = build(candidate, candidate.with_suffix('.zip'))
    print(json.dumps(report, indent=2))
    return candidate


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--name', required=True)
    parser.add_argument('--conversion', action='store_true')
    parser.add_argument('--reductions', action='store_true')
    parser.add_argument('--model', type=Path)
    parser.add_argument('--blend', type=float, default=0.0)
    parser.add_argument('--tables', action='store_true')
    parser.add_argument('--table-directory', type=Path)
    parser.add_argument('--table-max-pieces', type=int, choices=(3, 4, 5), default=3)
    args = parser.parse_args()
    create(args.name, args.conversion, args.reductions, args.model, args.blend, args.tables,
           args.table_directory, args.table_max_pieces)
