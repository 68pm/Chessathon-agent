"""Evaluate the frozen rejected residual model on new D65 descendants; never refit."""

import json
from collections import defaultdict
from pathlib import Path

import chess
import numpy as np

from scripts.overnight_geometry_trial import ROOT, check_stop, digest, save
from scripts.overnight_value_labels import restore
from training import rule_value
from training.game_feedback import phase

OUT = ROOT / 'runs/overnight-20260909/fresh-value-diagnosis-01'


def run():
    check_stop()
    assert not OUT.exists(), 'Preserve every evaluation; no implicit rerun.'
    source = ROOT / 'runs/overnight-20260909/rule-value-01'
    labels_path = ROOT / 'runs/overnight-20260909/development-values-01/state.json'
    labels = json.loads(labels_path.read_text(encoding='utf-8'))
    previous = json.loads((source / 'state.json').read_text(encoding='utf-8'))
    preparation = json.loads((source / 'preparation.json').read_text(encoding='utf-8'))
    assert labels['status'] == previous['status'] == 'complete'
    assert previous['passed'] is False
    assert digest(source / 'value.npz') == previous['model_sha256']
    assert digest(source / 'dataset.npz') == previous['dataset_sha256']
    training_keys = {r['key'] for r in preparation['rows'] if r['split'] == 0}
    candidates = [r for r in labels['rows'] if r['eligible']]
    assert len(candidates) == 31 and {r['split'] for r in candidates} == {'validation'}
    assert len({r['group'] for r in candidates}) == 1
    kept = [r for r in candidates if r['duplicate_key'] not in training_keys]
    exclusions = [r['id'] for r in candidates if r['duplicate_key'] in training_keys]
    assert kept, 'All positions collide with previous training.'
    with np.load(source / 'value.npz', allow_pickle=False) as model:
        parameters = (np.vstack((model['weights'], model['rule_weights'])), model['bias'].copy(), model['output'].copy())
    assert [p.shape for p in parameters] == [(781, 64), (64,), (64,)]
    assert all(np.isfinite(p).all() for p in parameters)
    blend = previous['selected_blend']
    # Stored output weights already contain the 200cp scale. Check reconstruction
    # against the exact previously saved predictions before seeing new results.
    with np.load(source / 'dataset.npz', allow_pickle=False) as dataset:
        mask = (dataset['split'] == 1) & (dataset['targeted'] == 1)
        old_x, old_base = dataset['x'][mask], dataset['base'][mask]
    with np.load(source / 'holdout-predictions.npz', allow_pickle=False) as saved:
        reconstructed = old_base + blend * np.clip(rule_value.forward(old_x, parameters)[0], -600, 600)
        max_reconstruction_error = float(np.max(np.abs(reconstructed - saved['prediction'])))
        assert max_reconstruction_error < .002
    # This diagnostic has only 31 positions. Use the readable evaluator directly,
    # avoiding another full-search import or compilation during a report task.
    classical = rule_value.load_classical().py_func
    old_rows = [r for r in preparation['rows'] if r['split'] == 1 and r['targeted']]
    for row, expected in zip(old_rows, old_base, strict=True):
        assert classical(*rule_value.arrays(chess.Board(row['fen'])), False) == expected
    boards = [restore(r) for r in kept]
    x = np.stack([rule_value.features(b) for b in boards])
    base = np.asarray([classical(*rule_value.arrays(b), False) for b in boards], dtype=np.float32)
    teacher = np.asarray([r['target_stm_cp'] for r in kept], dtype=np.float32)
    prediction = base + blend * np.clip(rule_value.forward(x, parameters)[0], -600, 600)
    rows = [dict(id=row['id'], game=row['source_game_id'], root_ply=row['root_ply'],
        branch=row['branch'], descendant_plies=row['descendant_plies'], phase=phase(board),
        fen=board.fen(), target=float(target), classical=float(before), prediction=float(after),
        before_error=abs(float(before - target)), after_error=abs(float(after - target)))
        for row, board, target, before, after in zip(kept, boards, teacher, base, prediction, strict=True)]

    def summarize(items):
        return dict(count=len(items), classical_mae=sum(r['before_error'] for r in items) / len(items),
            model_mae=sum(r['after_error'] for r in items) / len(items),
            improved=sum(r['after_error'] < r['before_error'] for r in items),
            worsened=sum(r['after_error'] > r['before_error'] for r in items))

    phases, games = defaultdict(list), defaultdict(list)
    for row in rows:
        phases[row['phase']].append(row)
        games[row['game']].append(row)
    paths = [Path(__file__), Path(rule_value.__file__), labels_path,
        source / 'state.json', source / 'preparation.json', source / 'value.npz',
        source / 'dataset.npz', source / 'holdout-predictions.npz',
        ROOT / 'docs/OVERNIGHT_FRESH_VALUE_DIAGNOSIS_20260909.md']
    OUT.mkdir()
    report = dict(status='complete', sources={str(p.relative_to(ROOT)): digest(p) for p in paths},
        selected_blend=blend, previous_model_passed=False, model_changed=False,
        reconstruction_error_cp=max_reconstruction_error, excluded_training_collisions=exclusions,
        overall=summarize(rows), by_phase={k: summarize(v) for k, v in phases.items()},
        by_game={k: summarize(v) for k, v in games.items()}, rows=rows,
        scope='New source-group diagnostic of the frozen rejected model. No fit, parameter/blend selection, runtime integration, release promotion or Elo claim. Original failed gates remain failed.')
    save(OUT / 'diagnosis.json', report)
    np.savez_compressed(OUT / 'predictions.npz', teacher=teacher, classical=base, prediction=prediction)
    print(json.dumps({k: v for k, v in report.items() if k in ('status', 'overall', 'by_phase', 'by_game', 'excluded_training_collisions')}, indent=2))


if __name__ == '__main__':
    run()
