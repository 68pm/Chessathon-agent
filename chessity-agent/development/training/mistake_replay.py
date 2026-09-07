"""Bounded teacher-guided mistake replay, with real parameter updates and fresh probes."""

import os

for _variable in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ[_variable] = '1'

import argparse
import ast
import hashlib
import json
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import chess
import numpy as np

from experiments.compiled_core import classical
from experiments.compiled_driver import arrays
from scripts.alien_rating_ladder import save_json, sha256
from scripts.improvement_audit import evaluate
from scripts.magnus_benchmark import SF, manifest
from training.counterfactual_value import prepare as prepare_pairs
from training.counterfactual_value import restore_root
from training.fastchess_data import ROOT
from training.paired_residual import backprop
from training.puzzle_verifier import Verifier, duplicate_key
from training.residual_value import features, forward


def stop_check():
    if any((ROOT / flag).exists() for flag in ['STOP_TRAINING', 'STOP_BENCHMARK']):
        raise InterruptedError('User stop flag')


def endpoint_loss_gradient(x, target, parameters, blend):
    prediction, pre, hidden = forward(x, parameters)
    error = blend * np.clip(prediction, -2.5, 2.5) - target
    magnitude = np.abs(error)
    loss = float(np.mean(np.where(magnitude <= 1, .5 * error**2, magnitude - .5)))
    derivative = np.clip(error, -1, 1) * blend / len(x)
    derivative *= (prediction > -2.5) & (prediction < 2.5)
    return loss, backprop(x, derivative, parameters, pre, hidden)


def pair_loss_gradient(x, base, signs, margin, parameters, blend):
    flat = x.reshape(-1, x.shape[-1])
    prediction, pre, hidden = forward(flat, parameters)
    values = signs * (base / 200 + blend * np.clip(prediction, -2.5, 2.5).reshape(-1, 2))
    z = margin - (values[:, 0] - values[:, 1])
    loss = float(np.mean(np.logaddexp(0, z)))
    scale = np.exp(-np.logaddexp(0, -z)) * blend / len(x)
    derivative = np.column_stack((-scale * signs[:, 0], scale * signs[:, 1])).ravel()
    derivative *= (prediction > -2.5) & (prediction < 2.5)
    return loss, backprop(flat, derivative, parameters, pre, hidden)


def corrected(analysis, best, tolerance=50):
    # Equivalent good choices count: teacher top-one identity is not required.
    if len(analysis) != 2 or len(best) != 2:
        return False
    return all(a['cp'] is not None and b['cp'] is not None and a.get('mate') is None
               and b.get('mate') is None and a['cp'] >= b['cp'] - tolerance
               for a, b in zip(analysis, best, strict=True))


def partition(rows):
    counts = Counter(r['group'] for r in rows)
    if len(counts) < 2:
        raise ValueError('Need at least two distinct starting families; do not split related endpoints.')
    # Choose by counts and stable identity, never by candidate predictions.
    heldout = min(counts, key=lambda g: (abs(counts[g] / len(rows) - .25), g))
    return [dict(r, split=int(r['group'] == heldout)) for r in rows], heldout


def prepare(plan, out, ordinary_manifest):
    protected = {duplicate_key(chess.Board(r['fen'])) for r in ordinary_manifest['rows']}
    rows, rejected, seen = [], [], set()
    for source in plan['sources']:
        stop_check()
        paired = out / ('pairs-' + source['label'])
        prepare_pairs(ROOT / source['audit'], ROOT / source['matches'], paired, max_pairs=4)
        originals = {r['id']: r for r in map(json.loads, (ROOT / source['audit'] / 'positions.jsonl').read_text().splitlines())}
        for pair in map(json.loads, (paired / 'verified-pairs.jsonl').read_text().splitlines()):
            root = dict(originals[pair['source_id']])
            root['id'] = source['label'] + ':' + root['id']
            board = restore_root(root)
            group = duplicate_key(board.root())
            endpoints = [chess.Board(pair['branches'][name]['start_fen']) for name in ['best', 'played']]
            for b, name in zip(endpoints, ['best', 'played'], strict=True):
                for move in pair['branches'][name]['history']:
                    b.push_uci(move)
                assert b.fen() == pair['branches'][name]['fen']
            keys = [duplicate_key(b) for b in endpoints]
            reason = None
            if len(set(keys)) != 2 or any(k in protected or k in seen for k in keys):
                reason = 'Duplicate or original broad-dataset collision'
            elif any(b.is_check() or b.is_game_over(claim_draw=True) or b.is_repetition(2)
                     or b.halfmove_clock >= 70 for b in endpoints):
                reason = 'Endpoint needs tactical, terminal or history handling'
            if reason:
                rejected.append(dict(id=root['id'], reason=reason))
                continue
            seen.update(keys)
            rows.append(dict(root=root, group=group, pair=pair,
                x=[features(b).tolist() for b in endpoints],
                base=[int(classical(*arrays(b))) for b in endpoints],
                signs=[1 if b.turn == board.turn else -1 for b in endpoints],
                cp=[pair['branches'][name]['analysis'][-1]['cp'] for name in ['best', 'played']],
                margin=min(1., min(a - b for a, b in zip(pair['branches']['best']['root_pov_cp'],
                    pair['branches']['played']['root_pov_cp'], strict=True)) / 200)))
    rows, heldout = partition(rows)
    assert len(rows) <= 20 and any(r['split'] == 0 for r in rows) and any(r['split'] == 1 for r in rows)
    save_json(out / 'dataset.json', dict(status='complete', heldout_family=heldout, rows=rows, rejected=rejected))
    return rows


def fit_round(path, parameters, ordinary, rows, recipe, seed, targeted):
    if path.exists():
        raise ValueError('Preserve completed or interrupted round; never overwrite weights.')
    path.mkdir(parents=True)
    p = [a.copy() for a in parameters]
    m, v = [np.zeros_like(a) for a in p], [np.zeros_like(a) for a in p]
    rng = np.random.default_rng(seed)
    broad = np.flatnonzero(ordinary['split'] == 0)
    x, base, signs, cp, margin = [np.asarray([r[k] for r in rows], dtype=np.float32)
                               for k in ['x', 'base', 'signs', 'cp', 'margin']]
    used, exposure = [], Counter()
    for step in range(1, recipe['updates_per_round'] + 1):
        stop_check()
        idx = rng.choice(broad, recipe['batch_size'], replace=False)
        used.extend(map(int, idx))
        _, gradients = endpoint_loss_gradient(ordinary['x'][idx], ordinary['y'][idx], p, recipe['blend'])
        if targeted:
            _, endpoint = endpoint_loss_gradient(x.reshape(-1, 768),
                ((cp - base) / 200).ravel(), p, recipe['blend'])
            _, preference = pair_loss_gradient(x, base, signs, margin, p, recipe['blend'])
            gradients = [g + .25 * e + .1 * r for g, e, r in zip(gradients, endpoint, preference, strict=True)]
            exposure.update(r['root']['id'] for r in rows)
        for i in range(3):
            g = gradients[i] + .00001 * p[i]
            m[i] = .9 * m[i] + .1 * g
            v[i] = .999 * v[i] + .001 * g * g
            p[i] -= recipe['learning_rate'] * (m[i] / (1 - .9**step)) / (np.sqrt(v[i] / (1 - .999**step)) + 1e-8)
        assert all(np.isfinite(a).all() for a in p)
    np.savez_compressed(path / 'value.npz', weights=p[0], bias=p[1], output=p[2] * 200)
    save_json(path / 'fit.json', dict(status='complete', targeted=targeted, updates=recipe['updates_per_round'],
        seed=seed, model_sha256=sha256(path / 'value.npz'), replay_exposure=dict(exposure),
        broad_index_sha256=hashlib.sha256(np.asarray(used, dtype=np.int64).tobytes()).hexdigest()))
    return p


def snapshot(base, target, model, blend):
    if target.exists():
        raise ValueError('Preserve frozen probe snapshot')
    shutil.copytree(base, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(model, target / 'models/value.npz')
    config = json.loads((target / 'runtime.json').read_text())
    config.update(residual_value=True, value_blend=blend)
    save_json(target / 'runtime.json', config)


def probe(path, rows, out):
    roots = out.with_suffix('.jsonl')
    roots.write_text(''.join(json.dumps(r['root']) + '\n' for r in rows), encoding='utf-8')
    with out.with_suffix('.log').open('w', encoding='utf-8') as log:
        subprocess.run([sys.executable, '-m', 'scripts.improvement_probe', '--candidate', str(path),
            '--audit', str(roots), '--out', str(out), '--seconds', '20', '--nodes', '250000'],
            cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=300,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
    return json.loads(out.read_text())['results']


def review_choices(rows, choices, cache_path):
    cached = {r['key']: r for r in map(json.loads, cache_path.read_text().splitlines())} if cache_path.exists() else {}
    teacher, records, new_nodes = Verifier(SF), [], 0
    try:
        for row, choice in zip(rows, choices, strict=True):
            stop_check()
            root = row['root']
            assert root['id'] == choice['id']
            board = restore_root(root)
            values = []
            for index, budget in enumerate([80000, 320000]):
                reference = root['verification'][index]
                key = root['id'] + ':' + choice['uci'] + ':' + str(budget)
                if key in cached:
                    value = cached[key]['analysis']
                elif choice['uci'] == root['played']:
                    value = reference['played']
                elif choice['uci'] == reference['best']['pv'][0]:
                    value = reference['best']
                else:
                    value = evaluate(teacher.engine, board, budget, chess.Move.from_uci(choice['uci']))
                    new_nodes += budget
                    record = dict(key=key, analysis=value)
                    with cache_path.open('a', encoding='utf-8') as stream:
                        stream.write(json.dumps(record) + '\n')
                    cached[key] = record
                values.append(value)
            best = [p['best'] for p in root['verification']]
            regret = [min(1000, max(0, b['cp'] - a['cp'])) if a['cp'] is not None
                      else 1000 if a['mate'] < 0 else 0 for a, b in zip(values, best, strict=True)]
            records.append(dict(id=root['id'], uci=choice['uci'], corrected=corrected(values, best),
                analysis=values, regret=regret, mate_loss=all(a.get('mate') is not None and a['mate'] < 0 for a in values)))
    finally:
        teacher.close()
    return dict(records=records, corrected=sum(r['corrected'] for r in records),
        mean_regret=np.mean([r['regret'] for r in records], axis=0).tolist(),
        mate_losses=sum(r['mate_loss'] for r in records), new_teacher_nodes=new_nodes)


def validation(parameters, ordinary, blend):
    valid = np.flatnonzero(ordinary['split'] == 1)
    predictions = np.concatenate([forward(ordinary['x'][idx], parameters)[0] for idx in np.array_split(valid, 8)])
    errors = ordinary['base'][valid] + 200 * blend * np.clip(predictions, -2.5, 2.5) - ordinary['cp'][valid]
    return float(np.mean(np.minimum(errors**2, 1000000)))


def main(plan_path):
    plan = json.loads(plan_path.read_text())
    prerequisite = json.loads((ROOT / plan['wait_for']).read_text())
    assert prerequisite['status'] == 'complete', 'Never train while the timed battery is active.'
    out = ROOT / plan['output']
    if out.exists():
        raise ValueError('Single pilot; preserve any earlier complete or interrupted output.')
    out.mkdir(parents=True)
    base, recipe = ROOT / plan['base'], plan['recipe']
    base_files = manifest(base)
    def classical_ast(path):
        return ast.dump(next(n for n in ast.parse(path.read_text()).body
                             if isinstance(n, ast.FunctionDef) and n.name == 'classical'))
    assert classical_ast(base / 'engine/compiled_core.py') == classical_ast(ROOT / 'experiments/compiled_core.py')
    save_json(out / 'context.json', dict(plan_sha256=sha256(plan_path), base_files=base_files,
        source_code_sha256=sha256(__file__), initial_model_sha256=sha256(ROOT / plan['initial_model']),
        ordinary_sha256=sha256(ROOT / plan['ordinary']),
        ordinary_manifest_sha256=sha256(ROOT / plan['ordinary_manifest']),
        prerequisite_sha256=sha256(ROOT / plan['wait_for']), status='started'))
    ordinary_path = ROOT / plan['ordinary']
    with np.load(ordinary_path, allow_pickle=False) as data:
        ordinary = dict(data)
    ordinary_manifest = json.loads((ROOT / plan['ordinary_manifest']).read_text())
    rows = prepare(plan, out, ordinary_manifest)
    train, holdout = [r for r in rows if r['split'] == 0], [r for r in rows if r['split'] == 1]
    with np.load(ROOT / plan['initial_model'], allow_pickle=False) as data:
        # Reuse only our own learned features. A zero correction head starts at the
        # selected classical evaluator, rather than enabling a rejected old net.
        initial = [data['weights'], data['bias'], np.zeros_like(data['output'])]
    candidate, control = [a.copy() for a in initial], [a.copy() for a in initial]
    cache = out / 'choice-cache.jsonl'
    baseline = review_choices(train, probe(base, train, out / 'baseline-train.json'), cache)
    unresolved = {r['id'] for r in baseline['records'] if not r['corrected']}
    if not unresolved:
        save_json(out / 'report.json', dict(status='complete', gate_passed=False, promotion=False,
            reason='The selected baseline already solves every accepted training root within50cp; no retry training needed.',
            training_roots=len(train), heldout_roots=len(holdout), baseline_training=baseline))
        return
    rounds = []
    for number in range(1, recipe['max_rounds'] + 1):
        stop_check()
        seed = plan['seed'] + number
        cp, tp = out / f'round-{number}-control', out / f'round-{number}-candidate'
        active = [r for r in train if r['root']['id'] in unresolved]
        control = fit_round(cp, control, ordinary, active, recipe, seed, False)
        candidate = fit_round(tp, candidate, ordinary, active, recipe, seed, True)
        snapshot(base, tp / 'agent', tp / 'value.npz', recipe['blend'])
        choices = review_choices(train, probe(tp / 'agent', train, out / f'round-{number}-probe.json'), cache)
        rounds.append(dict(round=number, replayed_ids=sorted(unresolved), training_replay=choices,
                           model_sha256=sha256(tp / 'value.npz')))
        unresolved = {r['id'] for r in choices['records'] if not r['corrected']}
        save_json(out / 'progress.json', dict(status='replaying', completed_rounds=rounds,
            training_roots=len(train), heldout_roots=len(holdout)))
        print(f"Replay round {number}: {choices['corrected']}/{len(train)} verified within50cp", flush=True)
        if not unresolved:
            break
    snapshot(base, cp / 'agent', cp / 'value.npz', recipe['blend'])
    heldout_reviews = {}
    for name, path in [('baseline', base), ('control', cp / 'agent'), ('candidate', tp / 'agent')]:
        heldout_reviews[name] = review_choices(holdout, probe(path, holdout, out / f'heldout-{name}.json'), cache)
    broad = {name: validation(p, ordinary, recipe['blend'])
             for name, p in [('initial', initial), ('control', control), ('candidate', candidate)]}
    a, b, c = [heldout_reviews[k] for k in ['baseline', 'control', 'candidate']]
    improved = (rounds[-1]['training_replay']['corrected'] > baseline['corrected']
        and all(x < min(y, z) for x, y, z in zip(c['mean_regret'], a['mean_regret'], b['mean_regret'], strict=True))
        and c['mate_losses'] <= min(a['mate_losses'], b['mate_losses'])
        and broad['candidate'] <= 1.02 * min(broad['initial'], broad['control']))
    assert manifest(base) == base_files
    result = dict(status='complete', base=plan['base'], promotion=False, gate_passed=improved,
        training_roots=len(train), heldout_roots=len(holdout), rounds=rounds, baseline_training=baseline,
        heldout=heldout_reviews, broad_validation_capped_mse_cp=broad,
        candidate_path=str((tp / 'agent').relative_to(ROOT)),
        control_path=str((cp / 'agent').relative_to(ROOT)), plan_sha256=sha256(plan_path),
        scope='Actual supervised parameter updates and retries, at most three rounds. '
              'Training-root improvement can be memorisation; one held-out family is a narrow diagnostic. '
              'No exact-best-move proof, reward for every move in a win, automatic promotion or Elo claim. '
              'A passed gate requires read-only and small real-clock matches before practical release.')
    save_json(out / 'report.json', result)
    print(json.dumps(dict(status='complete', gate_passed=improved, rounds=len(rounds),
                         train=len(train), holdout=len(holdout))), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    main(parser.parse_args().plan)
