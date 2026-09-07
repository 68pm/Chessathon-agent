"""Train an original compact residual evaluator used at every search leaf.

Uses existing CC0 engine-labelled positions, preserving their ECO-group splits.
Newly audited development positions can supply extra verified correction targets.
No published network or runtime lookup table is used.
"""

import os

for _variable in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS']:
    os.environ[_variable] = '1'

import argparse
import json
from pathlib import Path

import chess
import numpy as np

from engine.features import encode
from experiments.compiled_core import classical
from experiments.compiled_driver import arrays
from scripts.alien_rating_ladder import save_json, sha256
from training.fastchess_data import ROOT
from training.puzzle_verifier import duplicate_key


def features(board):
    return encode(board)[:768]


def forward(x, parameters):
    w, b, out = parameters
    pre = x @ w + b
    hidden = np.clip(pre, 0.0, 1.0)
    return hidden @ out, pre, hidden


def gradients(x, target, parameters):
    prediction, pre, hidden = forward(x, parameters)
    difference = prediction - target
    derivative = np.clip(difference, -1, 1) / len(x)
    dwout = hidden.T @ derivative
    dhidden = derivative[:, None] * parameters[2][None, :]
    dhidden *= (pre > 0) & (pre < 1)
    return [x.T @ dhidden, dhidden.sum(axis=0), dwout]


def prepare(source, audit, out, seed, train_limit, valid_limit):
    rng = np.random.default_rng(seed)
    with np.load(source, allow_pickle=False) as data:
        fens, cp, split = data['fen'], data['cp'], data['split']
    supplemental = []
    if audit and audit.exists():
        for line in audit.read_text().splitlines():
            row = json.loads(line)
            lines = row.get('verification', [])
            if len(lines) != 2:
                continue
            scores = [v['best']['cp'] for v in lines]
            if None in scores or abs(scores[0] - scores[1]) > 100:
                continue
            if row['clock_ms'] > 0 and abs(scores[1]) <= 1500:
                supplemental.append((row['fen'], scores[1], row['id']))
    dev_keys = {duplicate_key(chess.Board(f)) for f, _, _ in supplemental}
    selected, keys = [], set()
    # Validation selected first. Whole ECO source splits are retained; exact/mirror
    # collisions are removed across this new evaluator's own train/validation split.
    for partition, limit in [(1, valid_limit), (0, train_limit)]:
        candidates = np.flatnonzero((split == partition) & np.isfinite(cp) & (np.abs(cp) <= 1500))
        rng.shuffle(candidates)
        count = 0
        for index in candidates:
            board = chess.Board(str(fens[index]))
            if board.is_check() or board.halfmove_clock >= 70 or board.is_game_over():
                continue
            key = duplicate_key(board)
            if key in keys or (partition == 1 and key in dev_keys):
                continue
            keys.add(key)
            selected.append((board, float(cp[index]), partition, int(index)))
            count += 1
            if count >= limit:
                break
    for fen, score, identity in supplemental:
        board = chess.Board(fen)
        if board.is_check() or board.halfmove_clock >= 70 or board.is_game_over():
            continue
        key = duplicate_key(board)
        if key not in keys:
            selected.append((board, float(score), 0, identity))
            keys.add(key)
    x = np.asarray([features(b) for b, _, _, _ in selected], dtype=np.float32)
    base = np.array([classical(*arrays(b)) for b, _, _, _ in selected], dtype=np.float32)
    teacher = np.array([score for _, score, _, _ in selected], dtype=np.float32)
    partition = np.array([s for _, _, s, _ in selected], dtype=np.uint8)
    y = np.clip((teacher - base) / 200.0, -2.5, 2.5)
    np.savez_compressed(out / 'dataset.npz', x=x, y=y, base=base, cp=teacher, split=partition)
    save_json(out / 'dataset-manifest.json', dict(source=str(source.relative_to(ROOT)), source_sha256=sha256(source),
              source_licence='CC0 https://database.lichess.org/', seed=seed, train=int(sum(partition == 0)),
              validation=int(sum(partition == 1)), supplemental_available=len(supplemental),
              rows=[dict(source_index=identity, split=int(s), fen=b.fen()) for b, _, s, identity in selected],
              learning_target='clipped teacher-minus-classical residual in 200cp units',
              limitations='Older PGN annotation teacher versions/depths uncontrolled. ECO grouping plus exact/mirror exclusion reduces leakage; semantic overlap remains possible. Validation is a diagnostic, not a rating test. Supplemental verification uses actual history, while this static network cannot represent repetition history.'))
    return x, y, base, teacher, partition


def train(source, audit, out, epochs=12, seed=2026090714, train_limit=30000, valid_limit=4000):
    if out.exists():
        raise ValueError('Preserve completed/partial fits; select a fresh output directory.')
    out.mkdir(parents=True)
    x, y, base, teacher, split = prepare(source, audit, out, seed, train_limit, valid_limit)
    train_idx, valid = np.flatnonzero(split == 0), np.flatnonzero(split == 1)
    assert len(train_idx) and len(valid)
    rng = np.random.default_rng(seed)
    p = [rng.normal(0, 0.025, (768, 32)).astype(np.float32),
         np.full(32, 0.25, dtype=np.float32), np.zeros(32, dtype=np.float32)]
    m, v = [np.zeros_like(a) for a in p], [np.zeros_like(a) for a in p]
    baseline = float(np.mean(np.minimum((base[valid] - teacher[valid]) ** 2, 1000000)))
    best, best_epoch, best_blend, steps, stale = baseline, 0, 0.0, 0, 0
    best_p, logs = [a.copy() for a in p], []
    for epoch in range(1, epochs + 1):
        if (ROOT / 'STOP_TRAINING').exists():
            raise InterruptedError('STOP_TRAINING requested')
        indices = rng.permutation(train_idx)
        for offset in range(0, len(indices), 256):
            batch = indices[offset:offset + 256]
            grads = gradients(x[batch], y[batch], p)
            steps += 1
            for i in range(3):
                gradient = grads[i] + 0.00001 * p[i]
                m[i] = 0.9 * m[i] + 0.1 * gradient
                v[i] = 0.999 * v[i] + 0.001 * gradient * gradient
                p[i] -= 0.002 * (m[i] / (1 - 0.9**steps)) / (np.sqrt(v[i] / (1 - 0.999**steps)) + 1e-8)
        predictions = np.concatenate([forward(x[valid[i:i + 512]], p)[0] for i in range(0, len(valid), 512)]) * 200
        losses = {str(blend): float(np.mean(np.minimum((base[valid] + blend * np.clip(predictions, -500, 500) - teacher[valid])**2, 1000000)))
                  for blend in (0.0, 0.25, 0.5, 1.0)}
        blend = min(losses, key=losses.get)
        loss = losses[blend]
        if loss < best:
            best, best_epoch, best_blend, stale = loss, epoch, float(blend), 0
            best_p = [a.copy() for a in p]
        else:
            stale += 1
        logs.append(dict(epoch=epoch, validation_capped_mse_cp=losses))
        save_json(out / 'progress.json', dict(status='training', epoch=epoch, best_epoch=best_epoch,
                  classical_validation_capped_mse_cp=baseline, best_validation_capped_mse_cp=best))
        print(f'Epoch {epoch}: validation {loss:.1f} vs classical {baseline:.1f}; retained {best_epoch}', flush=True)
        if stale >= 3:
            break
    np.savez_compressed(out / 'value.npz', weights=best_p[0], bias=best_p[1], output=best_p[2] * 200)
    save_json(out / 'training.json', dict(status='complete', architecture='768 sparse piece-square inputs, 32 clipped-ReLU hidden, one residual value output',
              initialisation='original random weights; zero output at epoch zero', seed=seed,
              source_code_sha256=sha256(__file__), source_dataset_sha256=sha256(source),
              dataset_sha256=sha256(out / 'dataset.npz'), model_sha256=sha256(out / 'value.npz'),
              epochs=logs, selected_epoch=best_epoch, value_blend=best_blend,
              classical_validation_capped_mse_cp=baseline, best_validation_capped_mse_cp=best,
              no_strength_claim='Static validation gate only. Requires speed, held-out move quality and frozen paired matches before promotion. This is supervised residual learning, not reinforcement learning.'))
    return out / 'value.npz'


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, default=ROOT / 'runs/unattended-20260905-away/data-300000/dataset.npz')
    parser.add_argument('--audit', type=Path, default=ROOT / 'runs/improvement-loop-20260907/baseline-audit/positions.jsonl')
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--epochs', type=int, default=12)
    parser.add_argument('--train-limit', type=int, default=30000)
    parser.add_argument('--valid-limit', type=int, default=4000)
    args = parser.parse_args()
    train(args.source, args.audit, args.out, args.epochs, train_limit=args.train_limit, valid_limit=args.valid_limit)
