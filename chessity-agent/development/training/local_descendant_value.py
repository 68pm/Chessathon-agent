"""Fit an original local clipped-ReLU residual at independently labeled leaves."""
import json
import os
from pathlib import Path

for _name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ[_name] = '1'

import numpy as np

from scripts.alien_rating_ladder import save_json, sha256

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/e55-local-value-20260908'


def pattern_parameters(centres):
    """Exactly represent max(0,1-HammingDistance/4) using the existing32 units."""
    assert len(centres) <= 32
    weights = np.zeros((768, 32), dtype=np.float32)
    bias = np.full(32, -1., dtype=np.float32)
    for i, centre in enumerate(centres):
        weights[:, i] = np.where(centre, .25, -.25)
        bias[i] = 1. - float(np.sum(centre)) / 4.
    return weights, bias


def main():
    path = OUT / 'training.json'
    assert not path.exists(), 'One fit; preserve every attempt'
    prep = json.loads((OUT / 'training-preparation.json').read_text())
    assert all(sha256(ROOT / p) == h for p,h in prep['source_files'].items())
    records = []
    for relative in prep['datasets']:
        for item in map(json.loads, (ROOT / relative).read_text().splitlines()):
            if item['eligible_static_target']:
                records.append(dict(item, source=relative))
    groups, rejected = {}, []
    for row in records:
        groups.setdefault(tuple(row['sparse_features_768']), []).append(row)
    accepted = []
    for group in groups.values():
        values = [r['teacher'][1]['cp'] for r in group]
        if max(values) - min(values) > 100:
            rejected.extend(dict(id=r['id'], source=r['source'], reason='conflicting identical piece input') for r in group)
        else:
            accepted.append(group[0])
            rejected.extend(dict(id=r['id'], source=r['source'], reason='duplicate piece input') for r in group[1:])
    assert len(accepted) >= 8 and len({r['group'] for r in accepted}) >= 2
    x = np.zeros((len(accepted),768), dtype=np.float32)
    target = []
    for i, row in enumerate(accepted):
        x[i, row['sparse_features_768']] = 1
        target.append(float(np.mean([v['cp'] for v in row['teacher']])) - row['static_stm_cp'])
    target = np.asarray(target, dtype=np.float64)
    by_group = {}
    for i,row in enumerate(accepted):
        by_group.setdefault(row['group'], []).append(i)
    for indices in by_group.values():
        indices.sort(key=lambda i:(-abs(target[i]),accepted[i]['id']))
    centres = []
    while len(centres) < min(32,len(accepted)):
        for group in sorted(by_group):
            if by_group[group] and len(centres) < 32:
                centres.append(by_group[group].pop(0))
    weights,bias = pattern_parameters(x[centres])
    hidden = np.clip(x @ weights + bias,0,1).astype(np.float64)
    # A single deterministic ridge fit. No clipping or resampled epochs.
    output = np.linalg.solve(hidden.T @ hidden + np.eye(32), hidden.T @ target)
    prediction = np.clip(hidden @ output,-1500,1500)
    model = OUT / 'prototype/models/value.npz'
    np.savez_compressed(model,weights=weights,bias=bias,output=output.astype(np.float32))
    report = dict(status='complete', architecture='768 sparse inputs /32 local clipped-ReLU features / trained residual output',
        hidden_activation='max(0,1-HammingDistance/4)', centres=centres,
        ridge=1., output_fits=1, epochs=0, target_clipped=False, runtime_cap_cp=1500,
        records=accepted, rejected=rejected, raw_targets_cp=target.tolist(), predictions_cp=prediction.tolist(),
        baseline_training_mae_cp=float(np.mean(abs(target))),
        fitted_training_mae_cp=float(np.mean(abs(target-prediction))),
        source_files=prep['source_files'], model_sha256=sha256(model),
        original_hidden_features=True, source_code_sha256=sha256(__file__),
        limitation='Exposed descendant training error, not held-out generalisation, reinforcement learning or Elo. No root value copied to leaves.')
    save_json(path,report)


if __name__ == '__main__':
    main()
