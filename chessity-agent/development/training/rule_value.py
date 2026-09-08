"""One fixed original rule-aware residual fit; no held-out descendant selection."""

import os

for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_name] = '1'

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import chess
import numpy as np

from scripts.overnight_geometry_trial import BASE, ROOT, check_stop, digest, save
from scripts.overnight_value_labels import duplicate, restore

OUT = ROOT / 'runs/overnight-20260909/rule-value-01'
SOURCE = ROOT / 'runs/unattended-20260905-away/data-300000/dataset.npz'
LABELS = ROOT / 'runs/overnight-20260909/value-labels-02/state.json'
SEED = 202609092330


def features(board):
    x = np.zeros(781, dtype=np.float32)
    for square, piece in board.piece_map().items():
        channel = piece.piece_type - 1 + (0 if piece.color == board.turn else 6)
        relative = square if board.turn else chess.square_mirror(square)
        x[channel * 64 + relative] = 1
    x[768:772] = [board.has_kingside_castling_rights(board.turn),
        board.has_queenside_castling_rights(board.turn),
        board.has_kingside_castling_rights(not board.turn),
        board.has_queenside_castling_rights(not board.turn)]
    if board.has_legal_en_passant():
        x[772 + chess.square_file(board.ep_square)] = 1
    x[780] = min(board.halfmove_clock, 70) / 70
    return x


def forward(x, parameters):
    weights, bias, output = parameters
    pre = x @ weights + bias
    hidden = np.clip(pre, 0., 1.)
    return hidden @ output, pre, hidden


def loss_and_gradients(x, target, parameters):
    prediction, pre, hidden = forward(x, parameters)
    error = prediction - target
    magnitude = np.abs(error)
    loss = np.mean(np.where(magnitude <= 1, .5 * error**2, magnitude - .5))
    derivative = np.clip(error, -1., 1.) / len(x)
    dhidden = derivative[:, None] * parameters[2][None, :]
    dhidden *= (pre > 0) & (pre < 1)
    return float(loss), [x.T @ dhidden, dhidden.sum(axis=0), hidden.T @ derivative]


def load_classical():
    # Load only v1.53's readable core; no full-search warmup or older evaluator.
    path = BASE / 'engine/compiled_core.py'
    spec = importlib.util.spec_from_file_location('frozen53_value_classical', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.classical


def arrays(board):
    pieces = np.zeros(128, dtype=np.int64)
    for square, piece in board.piece_map().items():
        pieces[chess.square_rank(square) * 16 + chess.square_file(square)] = (
            piece.piece_type * (1 if piece.color else -1))
    def square(value):
        return value // 8 * 16 + value % 8 if value is not None else -1
    rights = sum(bit * int(present) for bit, present in zip((1, 2, 4, 8), (
        board.has_kingside_castling_rights(True), board.has_queenside_castling_rights(True),
        board.has_kingside_castling_rights(False), board.has_queenside_castling_rights(False))))
    return pieces, np.array([1 if board.turn else -1, rights, square(board.ep_square),
        board.halfmove_clock, square(board.king(True)), square(board.king(False))], dtype=np.int64)


def prepare():
    labels = json.loads(LABELS.read_text(encoding='utf-8'))
    assert labels['status'] == 'complete'
    target_rows = [r for r in labels['rows'] if r['eligible']]
    protected = {r['duplicate_key'] for r in labels['rows']}
    assert len({r['duplicate_key'] for r in target_rows}) == len(target_rows)
    assert not ({r['group'] for r in target_rows if r['split'] == 'train'} &
                {r['group'] for r in target_rows if r['split'] == 'validation'})
    rng = np.random.default_rng(SEED)
    with np.load(SOURCE, allow_pickle=False) as data:
        fens, cp, split, group = data['fen'], data['cp'], data['split'], data['group']
    assert not (set(group[split == 0]) & set(group[split == 1]))
    rows, keys = [], set(protected)
    for partition, limit in ((1, 2000), (0, 20000)):
        indices = np.flatnonzero((split == partition) & np.isfinite(cp) & (np.abs(cp) <= 1500))
        rng.shuffle(indices)
        count = 0
        for index in indices:
            if count % 128 == 0:
                check_stop()
            board = chess.Board(str(fens[index]))
            if (not board.is_valid() or board.is_check() or board.halfmove_clock >= 70
                    or board.is_game_over(claim_draw=True)):
                continue
            key = duplicate(board)
            if key in keys:
                continue
            keys.add(key)
            rows.append(dict(fen=board.fen(), cp=float(cp[index]), split=partition,
                targeted=0, source_index=int(index), group=str(group[index]), key=key))
            count += 1
            if count == limit:
                break
        assert count == limit, 'Insufficient filtered broad data; do not silently alter bounds'
    for row in target_rows:
        board = restore(row)
        assert (not board.is_check() and not board.is_repetition(2)
                and not board.is_game_over(claim_draw=True) and board.halfmove_clock < 70)
        rows.append(dict(fen=board.fen(), cp=row['target_stm_cp'],
            split=int(row['split'] == 'validation'), targeted=1, source_id=row['id'],
            group=row['game_key'], key=duplicate(board)))
    assert not ({r['key'] for r in rows if r['split'] == 0} &
                {r['key'] for r in rows if r['split'] == 1})
    classical = load_classical()
    x = np.empty((len(rows), 781), dtype=np.float32)
    base = np.empty(len(rows), dtype=np.float32)
    for i, row in enumerate(rows):
        if i % 512 == 0:
            check_stop()
        board = chess.Board(row['fen'])
        x[i], base[i] = features(board), classical(*arrays(board), False)
    teacher = np.asarray([r['cp'] for r in rows], dtype=np.float32)
    partition = np.asarray([r['split'] for r in rows], dtype=np.uint8)
    targeted = np.asarray([r['targeted'] for r in rows], dtype=np.uint8)
    groups = np.asarray([r['group'] for r in rows])
    np.savez_compressed(OUT / 'dataset.npz', x=x, base=base, cp=teacher,
        y=np.clip((teacher - base) / 200, -3, 3), split=partition, targeted=targeted, group=groups)
    save(OUT / 'preparation.json', dict(seed=SEED, rows=rows,
        source_sha256={str(p.relative_to(ROOT)): digest(p) for p in (
            SOURCE, LABELS, BASE / 'engine/compiled_core.py', Path(__file__),
            ROOT / 'training/dataset.py', ROOT / 'docs/OVERNIGHT_VALUE_PLAN_20260909.md')},
        broad_train=20000, broad_validation=2000, target_train=labels['train'],
        target_validation=labels['validation'], epochs=20, batch_broad=256, batch_target=64,
        mixture=[.75, .25], learning_rate=.001, weight_decay=.00001,
        label_pov='side to move, verified training/dataset.py label.pov(board.turn)',
        baseline='Exact frozen v1.53 classical evaluation, conversion=False',
        selection='After epoch20 select blend using broad validation only; then assess descendant holdout once',
        limitation='Broad labels have uncontrolled teacher/depth; exact/mirror and ECO/source groups reduce but do not eliminate semantic overlap.'))
    return x, base, teacher, partition, targeted, groups


def predict(x, parameters):
    return np.concatenate([forward(x[i:i + 512], parameters)[0]
                           for i in range(0, len(x), 512)]) * 200


def run():
    from scripts.overnight_capacity import wait_for_capacity

    assert not (OUT / 'state.json').exists(), 'Preserve partial/completed fit; no implicit rerun'
    OUT.mkdir(parents=True, exist_ok=True)
    check_stop()
    wait_for_capacity(OUT / 'capacity.json', minimum_memory_mb=1400, wait_seconds=120)
    state = dict(status='preparing', passed=False, epochs=[])
    save(OUT / 'state.json', state)
    try:
        x, base, teacher, split, targeted, groups = prepare()
        rng = np.random.default_rng(SEED)
        p = [rng.normal(0, .025, (781, 64)).astype(np.float32),
             np.full(64, .25, dtype=np.float32), np.zeros(64, dtype=np.float32)]
        m, v = [np.zeros_like(a) for a in p], [np.zeros_like(a) for a in p]
        broad = np.flatnonzero((split == 0) & (targeted == 0))
        target = np.flatnonzero((split == 0) & (targeted == 1))
        game_groups = [target[groups[target] == g] for g in sorted(set(groups[target]))]
        y, steps = np.clip((teacher - base) / 200, -3, 3), 0
        for epoch in range(1, 21):
            check_stop()
            losses = []
            order = rng.permutation(broad)
            for offset in range(0, len(order), 256):
                check_stop()
                bi = order[offset:offset + 256]
                # Sample source games uniformly, then positions within each game.
                ti = np.asarray([rng.choice(game_groups[g])
                    for g in rng.integers(len(game_groups), size=min(64, len(target)))])
                lb, gb = loss_and_gradients(x[bi], y[bi], p)
                lt, gt = loss_and_gradients(x[ti], y[ti], p)
                losses.append(.75 * lb + .25 * lt)
                steps += 1
                for i in range(3):
                    gradient = .75 * gb[i] + .25 * gt[i] + .00001 * p[i]
                    m[i] = .9 * m[i] + .1 * gradient
                    v[i] = .999 * v[i] + .001 * gradient**2
                    p[i] -= .001 * (m[i] / (1 - .9**steps)) / (
                        np.sqrt(v[i] / (1 - .999**steps)) + 1e-8)
            assert all(np.isfinite(a).all() for a in p)
            state['epochs'].append(dict(epoch=epoch, training_huber=float(np.mean(losses))))
            state.update(status='training', steps=steps)
            save(OUT / 'state.json', state)
            print(json.dumps(state['epochs'][-1]), flush=True)
        # Freeze all weights BEFORE either validation is evaluated.
        np.savez_compressed(OUT / 'value.npz', weights=p[0][:768], rule_weights=p[0][768:],
            bias=p[1], output=p[2] * 200)
        bv = (split == 1) & (targeted == 0)
        residual = np.clip(predict(x[bv], p), -600, 600)
        options = {str(blend): float(np.mean(np.abs(base[bv] + blend * residual - teacher[bv])))
                   for blend in (0., .25, .5, 1.)}
        blend = float(min(options, key=options.get))
        tv = (split == 1) & (targeted == 1)
        target_before = float(np.mean(np.abs(base[tv] - teacher[tv])))
        target_prediction = base[tv] + blend * np.clip(predict(x[tv], p), -600, 600)
        target_after = float(np.mean(np.abs(target_prediction - teacher[tv])))
        state.update(status='complete', model_sha256=digest(OUT / 'value.npz'),
            dataset_sha256=digest(OUT / 'dataset.npz'), selected_blend=blend,
            broad_validation_mae_cp=options, target_validation_before_cp=target_before,
            target_validation_after_cp=target_after,
            passed=options[str(blend)] <= .98 * options['0.0'] and target_after <= .9 * target_before,
            architecture='Original781x64 clipped-ReLU residual, rule-aware, capped600cp',
            no_strength_claim='Static validation only. No candidate selected or Elo established.')
        np.savez_compressed(OUT / 'holdout-predictions.npz', teacher=teacher[tv],
            classical=base[tv], prediction=target_prediction)
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        state['updated_utc'] = datetime.now(timezone.utc).isoformat()
        save(OUT / 'state.json', state)
    print(json.dumps({k: v for k, v in state.items() if k != 'epochs'}), flush=True)


if __name__ == '__main__':
    run()
