"""Read-only algebra and small matrix inference on the completed replay pilot.

No Numba, chess search, teacher calls, parameter fitting or candidate selection.
"""
import os

for _name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ[_name] = '1'

import hashlib
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parents[1]
    run = root / 'runs/improvement-loop-20260907/mistake-replay-01'
    out = root / 'runs/improvement-loop-20260907/learning-reachability-01/report.json'
    if out.exists():
        raise ValueError('Preserve the completed review; no unchanged rerun.')
    dataset_path = run / 'dataset.json'
    dataset = json.loads(dataset_path.read_text())
    completed = json.loads((run / 'report.json').read_text())
    assert completed['status'] == 'complete' and not completed['gate_passed']
    assert len(dataset['rows']) == 9
    model_paths = {name: run / f'round-3-{name}/value.npz' for name in ['candidate', 'control']}
    protected = {path: sha(path) for path in [dataset_path, *model_paths.values()]}
    agent_dir = root / completed['candidate_path']
    runtime = json.loads((agent_dir / 'runtime.json').read_text())
    blend = float(runtime['value_blend'])
    assert blend == .25
    source = (agent_dir / 'engine/compiled_core.py').read_text()
    assert 'blend * min(500.0, max(-500.0, residual))' in source
    cap = 500 * blend
    x = np.asarray([row['x'] for row in dataset['rows']], dtype=np.float32).reshape(-1, 768)
    inference = {}
    for name, path in model_paths.items():
        with np.load(path, allow_pickle=False) as model:
            pre = x @ model['weights'] + model['bias']
            hidden = np.clip(pre, 0, 1)
            raw = hidden @ model['output']
            inference[name] = dict(raw=raw, clipped=np.abs(raw) >= 500,
                active_hidden=np.sum(hidden != 0, axis=1),
                differentiable_hidden=np.sum((pre > 0) & (pre < 1), axis=1))
    rows = []
    for i, row in enumerate(dataset['rows']):
        base, signs = row['base'], row['signs']
        gap = signs[0] * base[0] - signs[1] * base[1]
        corners = [signs[0] * (base[0] + a) - signs[1] * (base[1] + b)
                   for a, b in itertools.product([-cap, cap], repeat=2)]
        assert min(corners) == gap - 2 * cap and max(corners) == gap + 2 * cap
        margin = 200 * row['margin']
        endpoints = []
        for j, label in enumerate(['best', 'played']):
            needed = row['cp'][j] - base[j]
            endpoints.append(dict(branch=label, classical_cp=base[j], teacher_cp=row['cp'][j],
                needed_residual_cp=needed, exact_teacher_target_reachable=abs(needed) <= cap,
                irreducible_absolute_error_cp=max(0, abs(needed) - cap),
                final={name: dict(raw_residual_cp=float(values['raw'][2*i+j]),
                    applied_residual_cp=float(blend * np.clip(values['raw'][2*i+j], -500, 500)),
                    output_clip_gradient_zero=bool(values['clipped'][2*i+j]),
                    active_hidden=int(values['active_hidden'][2*i+j]),
                    differentiable_hidden=int(values['differentiable_hidden'][2*i+j]))
                    for name, values in inference.items()}))
        rows.append(dict(id=row['root']['id'], split='heldout' if row['split'] else 'training',
            base_pair_gap_cp=gap, requested_pair_margin_cp=margin,
            maximum_possible_pair_gap_cp=max(corners),
            requested_pair_margin_reachable=max(corners) >= margin, endpoints=endpoints))
    result = dict(status='complete', utc=datetime.now(timezone.utc).isoformat(),
        source_sha256=sha(Path(__file__)), blend=blend, raw_residual_cap_cp=500,
        applied_residual_cap_cp=cap, dataset_sha256=sha(dataset_path),
        model_sha256={name: sha(path) for name, path in model_paths.items()},
        endpoint_count=18, endpoint_targets_outside_cap=sum(
            not e['exact_teacher_target_reachable'] for r in rows for e in r['endpoints']),
        unreachable_pair_margin_count=sum(not r['requested_pair_margin_reachable'] for r in rows),
        clipped_final_endpoints={name: int(v['clipped'].sum()) for name, v in inference.items()},
        rows=rows, promotion=False, fitted_updates=0, teacher_nodes=0,
        scope='Exposed completed-pilot data. Exact algebraic capacity limits and vectorized saved-model diagnostics, not compiled-runtime parity, new generalization evidence or proof of the sole cause of the failed match/heldout results.')
    assert all(sha(path) == digest for path, digest in protected.items())
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: result[k] for k in ['status', 'endpoint_count',
        'endpoint_targets_outside_cap', 'unreachable_pair_margin_count', 'clipped_final_endpoints',
        'fitted_updates', 'teacher_nodes', 'promotion']}))


if __name__ == '__main__':
    main()
