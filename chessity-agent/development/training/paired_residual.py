"""Matched residual-learning pilot using independently verified quiet alternatives."""

import os

for _variable in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ[_variable] = '1'

import argparse
import hashlib
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path

import chess
import numpy as np

from experiments.compiled_core import classical
from experiments.compiled_driver import arrays
from scripts.alien_rating_ladder import save_json, sha256
from training.fastchess_data import ROOT
from training.puzzle_verifier import duplicate_key
from training.residual_value import features, forward, gradients

RUN = ROOT / 'runs/improvement-loop-20260907'
SEED = 2026090712
SOURCES = [
    ('counterfactual-pilot-01', 'confirmation-01/rated/results.json'),
    ('cycle-03/successor-data', 'cycle-03/rated-compiled-reductions-v1/results.json'),
    ('cycle-04/successor-data', 'cycle-04/rated-compiled-rook-bishop-v1/results.json'),
    ('cycle-05/successor-data', 'cycle-05/rated-compiled-transposition-hints-v1/results.json'),
]


def backprop(x, derivative, parameters, pre, hidden):
    delta = derivative[:, None] * parameters[2][None, :]
    delta *= (pre > 0) & (pre < 1)
    return [x.T @ delta, delta.sum(axis=0), hidden.T @ derivative]


def ranking(x, base, signs, margin, parameters):
    """Total endpoint values are compared in the original mover's perspective."""
    shape = x.shape
    flat = x.reshape(-1, shape[-1])
    prediction, pre, hidden = forward(flat, parameters)
    clipped = np.clip(prediction, -2.5, 2.5).reshape(-1, 2)
    root_values = signs * (base / 200 + clipped)
    gap = root_values[:, 0] - root_values[:, 1]
    z = margin - gap
    loss = float(np.mean(np.logaddexp(0, z)))
    sigmoid = np.exp(-np.logaddexp(0, -z)) / len(x)
    derivative = np.column_stack((-sigmoid * signs[:, 0], sigmoid * signs[:, 1])).ravel()
    derivative *= (prediction > -2.5) & (prediction < 2.5)
    return loss, backprop(flat, derivative, parameters, pre, hidden), gap


def opening_family(game):
    eco = game.get('opening_group', '')
    if len(eco) == 3 and eco[1:].isdigit():
        number = int(eco[1:])
        if eco[0] == 'C':
            if number >= 60:
                return 'ruy-lopez'
            if 42 <= number <= 43:
                return 'petrov'
            if 50 <= number <= 59:
                return 'italian'
            if number <= 19:
                return 'french'
        if eco[0] == 'D' and 10 <= number <= 19:
            return 'slav'
        return 'eco:' + eco
    moves = game['opening']
    if moves[:5] == ['e2e4', 'e7e5', 'g1f3', 'b8c6', 'f1b5']:
        return 'ruy-lopez'
    if moves[:4] == ['e2e4', 'e7e5', 'g1f3', 'g8f6']:
        return 'petrov'
    return 'setup:' + hashlib.sha256(json.dumps(moves).encode()).hexdigest()[:16]


def holdout_groups(groups):
    """Count-only deterministic partition: no position scores or model outputs."""
    counts = Counter(groups)
    names = sorted(counts)
    if len(names) > 12:
        raise ValueError('This small pilot supports at most12 opening groups.')
    choices = []
    for size in range(1, len(names) - 1):
        for combo in itertools.combinations(names, size):
            valid = sum(counts[g] for g in combo)
            train = len(groups) - valid
            if train >= 8 and valid >= 4:
                tie = hashlib.sha256((str(SEED) + ':'.join(combo)).encode()).hexdigest()
                choices.append(((abs(valid / len(groups) - .25), size, tie), set(combo)))
    return min(choices, key=lambda item: item[0])[1] if choices else None


def prepare(out):
    original = RUN / 'residual-pilot-01'
    manifest = json.loads((original / 'dataset-manifest.json').read_text(encoding='utf-8'))
    previous = json.loads((original / 'training.json').read_text(encoding='utf-8'))
    assert previous['dataset_sha256'] == sha256(original / 'dataset.npz')
    assert previous['model_sha256'] == sha256(original / 'value.npz')
    protected = {duplicate_key(chess.Board(r['fen'])) for r in manifest['rows']}
    rows, quarantine, sources = [], [], []
    seen_ids = set()
    for pairdir, reportpath in SOURCES:
        pairdir, reportpath = RUN / pairdir, RUN / reportpath
        summary = json.loads((pairdir / 'report.json').read_text(encoding='utf-8'))
        source = json.loads(reportpath.read_text(encoding='utf-8'))
        digest = sha256(reportpath)
        assert source['status'] == summary['status'] == 'complete'
        assert summary['context']['source_sha256'] == digest
        assert summary['context']['validation_sha256'] == sha256(original / 'dataset-manifest.json')
        assert sha256(pairdir / 'verified-pairs.jsonl') == summary['pairs_sha256']
        games = {str(g['id']): g for g in source['games']}
        sources.append(dict(source=str(reportpath.relative_to(ROOT)), source_sha256=digest,
                            pairs=str((pairdir / 'verified-pairs.jsonl').relative_to(ROOT)),
                            pairs_sha256=summary['pairs_sha256']))
        for pair in map(json.loads, (pairdir / 'verified-pairs.jsonl').read_text(encoding='utf-8').splitlines()):
            assert pair['accepted'] and pair['id'].startswith(digest + ':') and pair['id'] not in seen_ids
            seen_ids.add(pair['id'])
            group = opening_family(games[pair['source_game_id'].split(':')[-1]])
            boards, signs, cp, bases, keys = [], [], [], [], []
            reason = None
            for label in ['best', 'played']:
                endpoint = pair['branches'][label]
                b = chess.Board(endpoint['start_fen'])
                for move in endpoint['history']:
                    b.push_uci(move)
                assert b.fen() == endpoint['fen'] and b.is_valid()
                key = duplicate_key(b)
                if b.is_check() or b.is_game_over(claim_draw=True) or b.is_repetition(2) or b.halfmove_clock >= 70:
                    reason = 'history-sensitive, terminal, check or draw-clock endpoint'
                    break
                if key in protected:
                    reason = 'exact/mirror collision with initial residual train/validation data'
                    break
                boards.append(features(b))
                signs.append(1 if b.turn == chess.Board(pair['root_fen']).turn else -1)
                cp.append(endpoint['analysis'][-1]['cp'])
                bases.append(classical(*arrays(b)))
                keys.append(key)
            if reason:
                quarantine.append(dict(id=pair['id'], reason=reason))
                continue
            if keys[0] == keys[1]:
                quarantine.append(dict(id=pair['id'], reason='identical/mirrored endpoint input within a pair'))
                continue
            margin = min(a - b for a, b in zip(pair['branches']['best']['root_pov_cp'],
                         pair['branches']['played']['root_pov_cp'], strict=True)) / 200
            assert margin >= .5
            rows.append(dict(id=pair['id'], group=group, x=boards, signs=signs, cp=cp, base=bases,
                             keys=keys, margin=min(1., margin)))
    key_groups = defaultdict(set)
    for row in rows:
        for key in row['keys']:
            key_groups[key].add(row['group'])
    kept, used = [], set()
    for row in rows:
        if any(len(key_groups[k]) > 1 or k in used for k in row['keys']):
            quarantine.append(dict(id=row['id'], reason='duplicate endpoint or cross-family collision'))
        else:
            kept.append(row)
            used.update(row['keys'])
    groups = [row['group'] for row in kept]
    heldout = holdout_groups(groups)
    report = dict(status='complete' if heldout else 'insufficient_data', original_dataset_sha256=sha256(original / 'dataset.npz'),
                  initial_model_sha256=sha256(original / 'value.npz'), sources=sources,
                  accepted_before_additional_filters=len(seen_ids), retained_pairs=len(kept),
                  groups=dict(Counter(groups)), heldout_groups=sorted(heldout or []), quarantine=quarantine,
                  source_code_sha256=sha256(__file__), seed=SEED,
                  scope='Counterfactual labels held out by broad opening family. Historic general-data/theory exposure remains possible. All data is development material.')
    if heldout:
        split = np.array([int(row['group'] in heldout) for row in kept], dtype=np.uint8)
        report.update(training_pairs=int(sum(split == 0)), validation_pairs=int(sum(split == 1)),
                      rows=[dict(id=row['id'], group=row['group'], split=int(s)) for row, s in zip(kept, split, strict=True)])
        np.savez_compressed(out / 'pairs.npz', **{key: np.asarray([r[key] for r in kept], dtype=np.float32)
                            for key in ['x', 'base', 'cp', 'signs', 'margin']}, split=split)
        report['prepared_pairs_sha256'] = sha256(out / 'pairs.npz')
    save_json(out / 'data-report.json', report)
    return report


def metrics(parameters, ordinary, pairs):
    valid = ordinary['split'] == 1
    prediction = np.concatenate([forward(x, parameters)[0] for x in np.array_split(ordinary['x'][valid], 8)])
    mse = float(np.mean(np.minimum((ordinary['base'][valid] + 200 * np.clip(prediction, -2.5, 2.5) - ordinary['cp'][valid])**2, 1000000)))
    mask = pairs['split'] == 1
    loss, _, gap = ranking(pairs['x'][mask], pairs['base'][mask], pairs['signs'][mask], pairs['margin'][mask], parameters)
    return dict(ordinary_validation_capped_mse_cp=mse, heldout_pair_margin_loss=loss,
                heldout_ordering_accuracy=float(np.mean(gap > 0)), heldout_predicted_gaps_cp=(gap * 200).tolist())


def fit(out, ordinary, pairs, initial, weight):
    p = [x.copy() for x in initial]
    m, v = [np.zeros_like(x) for x in p], [np.zeros_like(x) for x in p]
    train = np.flatnonzero(ordinary['split'] == 0)
    mask = pairs['split'] == 0
    px, pb, ps, pm = [pairs[key][mask] for key in ['x', 'base', 'signs', 'margin']]
    target = np.clip((pairs['cp'][mask] - pb) / 200, -2.5, 2.5).ravel()
    rng, step, logs = np.random.default_rng(SEED), 0, []
    for epoch in range(1, 7):
        if (ROOT / 'STOP_TRAINING').exists() or (ROOT / 'STOP_BENCHMARK').exists():
            raise InterruptedError('User stop flag')
        order = rng.permutation(train)
        for offset in range(0, len(order), 256):
            idx = order[offset:offset + 256]
            broad = gradients(ordinary['x'][idx], ordinary['y'][idx], p)
            endpoint = gradients(px.reshape(-1, 768), target, p)
            _, preference, _ = ranking(px, pb, ps, pm, p)
            step += 1
            for i in range(3):
                gradient = broad[i] + .25 * endpoint[i] + weight * preference[i] + .00001 * p[i]
                m[i] = .9 * m[i] + .1 * gradient
                v[i] = .999 * v[i] + .001 * gradient * gradient
                p[i] -= .0003 * (m[i] / (1 - .9**step)) / (np.sqrt(v[i] / (1 - .999**step)) + 1e-8)
        assert all(np.isfinite(x).all() for x in p)
        # Fixed epochs. Do not evaluate/select on held-out pairs between epochs.
        logs.append(dict(epoch=epoch, updates=step))
        print(f'{out.name}: epoch{epoch}/6', flush=True)
    out.mkdir()
    np.savez_compressed(out / 'value.npz', weights=p[0], bias=p[1], output=p[2] * 200)
    report = dict(status='complete', epochs=logs, pairwise_weight=weight, endpoint_weight=.25,
                  value_blend=1., model_sha256=sha256(out / 'value.npz'), metrics=metrics(p, ordinary, pairs))
    save_json(out / 'training.json', report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    if args.out.exists():
        raise ValueError('Use a fresh pilot directory; completed and partial fits are preserved.')
    args.out.mkdir(parents=True)
    report = prepare(args.out)
    print(json.dumps({k: v for k, v in report.items() if k not in ['rows', 'quarantine', 'sources']}), flush=True)
    if report['status'] != 'complete' or args.prepare_only:
        return
    with np.load(RUN / 'residual-pilot-01/dataset.npz', allow_pickle=False) as data:
        ordinary = dict(data)
    with np.load(args.out / 'pairs.npz', allow_pickle=False) as data:
        pairs = dict(data)
    with np.load(RUN / 'residual-pilot-01/value.npz', allow_pickle=False) as data:
        initial = [data['weights'], data['bias'], data['output'] / 200]
    initial_metrics = metrics(initial, ordinary, pairs)
    control = fit(args.out / 'control', ordinary, pairs, initial, 0.)
    candidate = fit(args.out / 'candidate', ordinary, pairs, initial, .1)
    a, b = control['metrics'], candidate['metrics']
    passed = (b['ordinary_validation_capped_mse_cp'] <= 1.01 * min(a['ordinary_validation_capped_mse_cp'], initial_metrics['ordinary_validation_capped_mse_cp'])
              and b['heldout_pair_margin_loss'] < a['heldout_pair_margin_loss']
              and b['heldout_ordering_accuracy'] >= a['heldout_ordering_accuracy'])
    save_json(args.out / 'review.json', dict(status='complete', gate_passed=passed, initial=initial_metrics,
              control=control, candidate=candidate, source_code_sha256=sha256(__file__),
              data_report_sha256=sha256(args.out / 'data-report.json'), epochs_selected='fixed6, no heldout checkpoint selection',
              next='Freeze in identical v1.41 runtimes and declare probes/matches.' if passed else 'No matches: critique failed pilot without repeating unchanged fit.',
              scope='Supervised development pilot, not a strength or reinforcement-learning claim.'))
    print(json.dumps(dict(gate_passed=passed, control=a, candidate=b)), flush=True)


if __name__ == '__main__':
    main()
