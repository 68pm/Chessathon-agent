"""One predeclared runtime-calibrated output-head fit and grouped endpoint holdout."""

import os

for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_name] = '1'

import argparse
import json
from pathlib import Path

import chess
import numpy as np

from scripts.overnight_geometry_trial import ROOT, check_stop, digest, save
from scripts.overnight_value_labels import restore
from training import rule_value

OUT = ROOT / 'runs/overnight-20260909/calibrated-head-01'
OLD = ROOT / 'runs/overnight-20260909/rule-value-01'


def active(board):
    phase = sum(len(board.pieces(p, c)) * v for p, v in ((2, 1), (3, 1), (4, 2), (5, 4)) for c in (True, False))
    return board.fullmove_number > 12 and phase > 8


def ridge_head(hidden, targets, weights, prior, penalty=50.):
    # All targets and output weights are in centipawns, not the old /200 units.
    matrix = hidden.astype(np.float64)
    lhs = matrix.T @ (weights[:, None] * matrix) + penalty * np.eye(matrix.shape[1])
    rhs = matrix.T @ (weights * targets) + penalty * prior
    answer = np.linalg.solve(lhs, rhs)
    assert np.isfinite(answer).all()
    return answer.astype(np.float32)


def prepare():
    assert not OUT.exists(), 'Preserve every attempt.'
    paths = [OLD / 'preparation.json', OLD / 'dataset.npz', OLD / 'value.npz',
        ROOT / 'runs/overnight-20260909/development-values-01/state.json',
        ROOT / 'runs/overnight-20260909/missing-alternatives-01/state.json',
        ROOT / 'runs/overnight-20260909/feedback-plan-countercheck-01/preparation.json',
        Path(__file__), Path(rule_value.__file__), ROOT / 'docs/OVERNIGHT_CALIBRATED_HEAD_20260909.md']
    old = json.loads(paths[0].read_text(encoding='utf-8'))
    dev, missing, planned = [json.loads(p.read_text(encoding='utf-8')) for p in paths[3:6]]
    assert dev['status'] == missing['status'] == 'complete'
    development = [r for d in (dev, missing) for r in d['rows'] if r['eligible'] and active(restore(r))]
    escalation = [r for r in missing['rows'] if not r['eligible'] and r['root_id'] == 'd65-black-35-capture']
    heldout = [r for r in planned['targets'] if r['guarded_residual_active'] and r['group'] not in planned['heldout_groups']]
    assert len(heldout) == 22 and len(escalation) == 2
    assert len({r['group'] for r in heldout}) == 2
    assert not ({r['group'] for r in heldout} & {r['group'] for r in development + escalation})
    protected = {r['duplicate_key'] for r in heldout}
    assert not (protected & {r['key'] for r in old['rows']})
    assert not (protected & {r['duplicate_key'] for r in development + escalation})
    indices = [i for i, r in enumerate(old['rows']) if active(chess.Board(r['fen']))]
    OUT.mkdir()
    save(OUT / 'preparation.json', dict(source_sha256={str(p.relative_to(ROOT)): digest(p) for p in paths},
        active_old_indices=indices, development=development, escalation=escalation, heldout=heldout,
        penalty=50, broad_weight=1, old_target_weight=50, new_target_weight=200, blend=.5, raw_cap=1200,
        maximum_new_teacher_nodes=12000000,
        attribution='D65 previously exposed validation is now development training. C09/D28 reserved before endpoint labels; already observed game roots, not fresh strength evidence.'))


def run():
    from scripts.overnight_capacity import wait_for_capacity
    from training.game_feedback import CachedTeacher

    prep_path = OUT / 'preparation.json'
    prep = json.loads(prep_path.read_text(encoding='utf-8'))
    assert not (OUT / 'state.json').exists()
    assert all(digest(ROOT / p) == h for p, h in prep['source_sha256'].items())
    check_stop()
    wait_for_capacity(OUT / 'capacity.json', minimum_memory_mb=1400, wait_seconds=120)
    state = dict(status='running', passed=False, preparation_sha256=digest(prep_path), escalation=[], holdout=[])
    save(OUT / 'state.json', state)
    teacher = CachedTeacher(ROOT / 'data/postgame-feedback/cache-v1', OUT)

    def label(row, budgets):
        check_stop()
        board = restore(row)
        values = [teacher.analyse(board, n) for n in budgets]
        cp = [v['cp'] for v in values]
        eligible = all(v is not None for v in cp) and all(v['mate'] is None for v in values)
        eligible = eligible and max(map(abs, cp)) <= 1500 and abs(cp[0] - cp[1]) <= 100
        return dict(source_id=row['id'], fen=row['fen'], teacher=values, eligible=eligible,
            target_stm_cp=sum(cp) / 2 if eligible else None)

    try:
        development = prep['development'].copy()
        for row in prep['escalation']:
            checked = label(row, (320000, 1280000))
            state['escalation'].append(checked)
            if checked['eligible']:
                development.append(dict(row, target_stm_cp=checked['target_stm_cp'], eligible=True))
            save(OUT / 'state.json', state)
        with np.load(OLD / 'value.npz', allow_pickle=False) as model:
            arrays = {k: model[k].copy() for k in model.files}
        encoder = np.vstack((arrays['weights'], arrays['rule_weights'])).astype(np.float64)
        bias, prior = arrays['bias'].astype(np.float64), arrays['output'].astype(np.float64)
        classical = rule_value.load_classical().py_func

        def positions(rows):
            boards = [chess.Board(r['fen']) for r in rows]
            x = np.stack([rule_value.features(b) for b in boards])
            base = np.asarray([classical(*rule_value.arrays(b), False) for b in boards], dtype=np.float64)
            cp = np.asarray([r['target_stm_cp'] for r in rows], dtype=np.float64)
            hidden = np.clip(x @ encoder + bias, 0., 1.)
            return hidden, base, cp

        with np.load(OLD / 'dataset.npz', allow_pickle=False) as data:
            idx = np.asarray(prep['active_old_indices'])
            hidden = np.clip(data['x'][idx] @ encoder + bias, 0., 1.)
            base, cp = data['base'][idx].astype(np.float64), data['cp'][idx].astype(np.float64)
            partition, targeted = data['split'][idx], data['targeted'][idx]
        train = partition == 0
        broad_validation = (partition == 1) & (targeted == 0)
        dh, db, dc = positions(development)
        weights = np.concatenate((np.where(targeted[train], 50., 1.), np.full(len(dh), 200.)))
        target = np.clip(2 * np.concatenate((cp[train] - base[train], dc - db)), -1200., 1200.)
        output = ridge_head(np.vstack((hidden[train], dh)), target, weights, prior)
        arrays['output'] = output
        check_stop()
        np.savez_compressed(OUT / 'value.npz', **arrays)
        state.update(status='model_frozen_before_holdout', model_sha256=digest(OUT / 'value.npz'),
            trained_parameters=64, development_count=len(development), broad_train=int(sum(train & (targeted == 0))),
            old_target_train=int(sum(train & (targeted == 1))))
        save(OUT / 'state.json', state)

        def assess(h, b, c):
            before = b + .5 * np.clip(h @ prior, -600., 600.)
            after = b + .5 * np.clip(h @ output.astype(np.float64), -1200., 1200.)
            return dict(count=len(c), old_mae=float(np.mean(np.abs(before - c))),
                new_mae=float(np.mean(np.abs(after - c))), classical_mae=float(np.mean(np.abs(b - c))))

        state['development_fit'] = assess(dh, db, dc)
        state['broad_validation'] = assess(hidden[broad_validation], base[broad_validation], cp[broad_validation])
        for row in prep['heldout']:
            checked = label(row, (80000, 320000))
            state['holdout'].append(checked)
            assert teacher.requested_nodes <= prep['maximum_new_teacher_nodes']
            save(OUT / 'state.json', state)
        eligible = [r for r in state['holdout'] if r['eligible']]
        state['grouped_holdout'] = assess(*positions(eligible)) if eligible else None
        d, b, h = state['development_fit'], state['broad_validation'], state['grouped_holdout']
        passed = bool(d['new_mae'] <= .9 * d['old_mae'] and b['new_mae'] <= 1.02 * b['old_mae']
            and h and h['count'] >= 8 and h['new_mae'] <= h['old_mae'])
        assert digest(OUT / 'value.npz') == state['model_sha256']
        state.update(status='complete', passed=passed,
            decision='needs_runtime_and_short_games' if passed else 'reject_static_gate', calibrated_elo=None)
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        teacher.close()
        state['requested_teacher_nodes'] = teacher.requested_nodes
        save(OUT / 'state.json', state)
        print(json.dumps({k: v for k, v in state.items() if k not in ('escalation', 'holdout')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    prepare() if parser.parse_args().prepare else run()
