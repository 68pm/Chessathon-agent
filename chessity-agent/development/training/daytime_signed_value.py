"""Fixed signed eight-unit value head, with positive/negative correction checks."""
import os

for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_name] = '1'

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import chess
import numpy as np

from scripts.daytime_common import BASE, ROOT, check_stop, digest, save
from scripts.overnight_capacity import wait_for_capacity
from scripts.overnight_value_labels import duplicate, restore
from training.residual_value import forward, gradients
from training.rule_value import arrays, features

OUT = ROOT / 'runs/daytime-20260909/signed-value-01'
PRIOR = ROOT / 'runs/daytime-20260909/small-value-01'
SOURCE = ROOT / 'runs/unattended-20260905-away/data-300000/dataset.npz'
LABELS = ROOT / 'runs/overnight-20260909/archive-values-03/state.json'
ADDITIONAL = ROOT / 'runs/daytime-20260909/signed-targets-01/state.json'
SEED = 2026090903


def active(board):
    phase = sum(len(board.pieces(p, c)) * v for p, v in ((2, 1), (3, 1), (4, 2), (5, 4)) for c in (True, False))
    return (phase > 8 and board.is_valid() and not board.is_check()
            and board.halfmove_clock < 70 and not board.is_repetition(2)
            and not board.is_game_over(claim_draw=True))


def load_classical():
    spec = importlib.util.spec_from_file_location('daytime_exact42_classical', BASE / 'engine/compiled_core.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.classical


def signed_parameters(rng):
    # Four units can add value; four can subtract it. Train input weights/biases,
    # preserving the fixed readout signs instead of collapsing all heads positive.
    return [rng.normal(0, .025, (768, 8)).astype(np.float32),
            np.full(8, .25, dtype=np.float32),
            np.asarray([.625] * 4 + [-.625] * 4, dtype=np.float32)]


def update_hidden(parameters, m, v, ga, gb, steps):
    for i in range(2):
        gradient = .8 * ga[i] + .2 * gb[i] + .00001 * parameters[i]
        m[i] = .9 * m[i] + .1 * gradient
        v[i] = .999 * v[i] + .001 * gradient * gradient
        parameters[i] -= .001 * (m[i] / (1 - .9**steps)) / (np.sqrt(v[i] / (1 - .999**steps)) + 1e-8)


def correction_cohorts(base, cp, residual):
    result = {}
    for label, mask in (('negative', cp - base <= -25), ('positive', cp - base >= 25)):
        assert int(mask.sum()) >= 50, 'Insufficient correction-cohort validation'
        result[label] = dict(n=int(mask.sum()), before=float(np.mean(abs(base[mask] - cp[mask]))),
            after=float(np.mean(abs(base[mask] + residual[mask] - cp[mask]))))
    return result


def cohorts_pass(cohorts):
    return all(row['after'] <= row['before'] for row in cohorts.values())


def select_targets(documents):
    chosen, conflicts, duplicates = {}, set(), []
    for document in documents:
        assert document['status'] == 'complete'
        for row in document['rows']:
            if not row['eligible'] or not active(restore(row)):
                continue
            assert row['target_stm_cp'] is not None and np.isfinite(row['target_stm_cp'])
            key = duplicate(restore(row))
            if key in chosen:
                duplicates.append(row['id'])
                if abs(chosen[key]['target_stm_cp'] - row['target_stm_cp']) > 100:
                    conflicts.add(key)
            else:
                chosen[key] = row
    return [row for key, row in chosen.items() if key not in conflicts], dict(
        duplicate_ids=duplicates, conflicting_keys=sorted(conflicts))


def prepare():
    check_stop()
    assert not OUT.exists(), 'Preserve every fit attempt.'
    OUT.mkdir(parents=True)
    wait_for_capacity(OUT / 'capacity.json', minimum_memory_mb=1400, wait_seconds=120)
    labels = json.loads(LABELS.read_text())
    additional = json.loads(ADDITIONAL.read_text())
    targets, target_exclusions = select_targets([labels, additional])
    assert len(targets) >= 16
    protected = {duplicate(restore(r)) for r in targets}
    assert len(protected) == len(targets)
    previous = json.loads((PRIOR / 'preparation.json').read_text())
    previous_result = json.loads((PRIOR / 'state.json').read_text())
    assert previous_result['status'] == 'complete' and not previous_result['passed']
    target_groups = {r['group'] for r in targets}
    excluded_groups = {r['group'] for r in previous['heldout_roots']} | target_groups
    protected.update(duplicate(chess.Board(r['fen'])) for r in previous['heldout_roots'])
    protected.update(duplicate(chess.Board(r['fen'])) for r in previous_result['holdout'])
    rng = np.random.default_rng(SEED)
    with np.load(SOURCE, allow_pickle=False) as data:
        fens, cp, split, groups = (data[k] for k in ('fen', 'cp', 'split', 'group'))
    assert all(not (set(groups[split == a]) & set(groups[split == b])) for a, b in ((0, 1), (0, 2), (1, 2)))
    rows, heldout, keys = [], [], set(protected)
    for part, limit in ((2, 24), (1, 1200), (0, 12000)):
        candidates = np.flatnonzero((split == part) & np.isfinite(cp) & (np.abs(cp) <= 1500))
        rng.shuffle(candidates)
        counts, count = {}, 0
        for index in candidates:
            check_stop()
            group = str(groups[index])
            if part != 0 and group in target_groups:
                continue
            if part == 2 and group in excluded_groups:
                continue
            if part == 2 and counts.get(group, 0) >= 2:
                continue
            board = chess.Board(str(fens[index]))
            if not active(board):
                continue
            key = duplicate(board)
            if key in keys:
                continue
            keys.add(key)
            row = dict(fen=board.fen(), cp=float(cp[index]), split=part, targeted=False,
                       source_index=int(index), group=group, key=key)
            (heldout if part == 2 else rows).append(row)
            count += 1
            counts[group] = counts.get(group, 0) + 1
            if count == limit:
                break
        assert count == limit, 'Insufficient eligible positions; preserve failure.'
    for row in targets:
        board = restore(row)
        rows.append(dict(fen=board.fen(), cp=row['target_stm_cp'], split=0, targeted=True,
            source_id=row['id'], group=row['group'], key=duplicate(board)))
    classical = load_classical()
    x = np.asarray([features(chess.Board(r['fen']))[:768] for r in rows], dtype=np.float32)
    base = np.asarray([classical(*arrays(chess.Board(r['fen'])), False) for r in rows], dtype=np.float32)
    teacher = np.asarray([r['cp'] for r in rows], dtype=np.float32)
    partition = np.asarray([r['split'] for r in rows])
    targeted = np.asarray([r['targeted'] for r in rows])
    np.savez_compressed(OUT / 'dataset.npz', x=x, base=base, cp=teacher,
        split=partition, targeted=targeted, y=np.clip((teacher - base) / 200., -2.5, 2.5))
    paths = [SOURCE, LABELS, ADDITIONAL, BASE / 'engine/compiled_core.py', Path(__file__),
        ROOT / 'scripts/daytime_common.py', ROOT / 'training/residual_value.py',
        ROOT / 'training/rule_value.py', ROOT / 'docs/DAYTIME_SIGNED_VALUE_20260909.md',
        ROOT / 'tests/test_daytime_signed_value.py', PRIOR / 'preparation.json', PRIOR / 'state.json']
    save(OUT / 'preparation.json', dict(seed=SEED, rows=rows, heldout_roots=heldout,
        source_sha256={str(p.relative_to(ROOT)):digest(p) for p in paths},
        targeted_train=len(targets), target_exclusions=target_exclusions, target_groups=sorted(target_groups),
        architecture='768/8 clipped ReLU with fixed +125cp/-125cp readouts', excluded_holdout_groups=sorted(excluded_groups),
        epochs=16, gradient_mix=[.8,.2], raw_runtime_cap_cp=500,
        target_group_policy='Archive and newly reviewed screen descendants are exposed training; exclude all target ECO groups from broad validation and new split2 reservations.'))
    return classical


def fit(classical):
    from training import game_feedback
    game_feedback.stop_check = check_stop
    prep = json.loads((OUT / 'preparation.json').read_text())
    assert all(digest(ROOT / p) == h for p,h in prep['source_sha256'].items())
    assert not (OUT / 'state.json').exists()
    with np.load(OUT / 'dataset.npz', allow_pickle=False) as data:
        x,y,base,cp,split,targeted = (data[k] for k in ('x','y','base','cp','split','targeted'))
    train = np.flatnonzero((split == 0) & ~targeted)
    target = np.flatnonzero(targeted)
    valid = np.flatnonzero(split == 1)
    rng = np.random.default_rng(SEED)
    parameters = signed_parameters(rng)
    m,v = [np.zeros_like(p) for p in parameters], [np.zeros_like(p) for p in parameters]
    baseline = float(np.mean(np.minimum((base[valid]-cp[valid])**2, 1000000)))
    best, retained, selected_epoch, selected_blend, steps = baseline, [p.copy() for p in parameters], 0, 0., 0
    state = dict(status='training', passed=False, epochs=[], holdout=[])
    save(OUT / 'state.json', state)
    for epoch in range(1,17):
        indices = rng.permutation(train)
        for offset in range(0,len(indices),256):
            check_stop()
            broad = indices[offset:offset+256]
            correction = rng.choice(target,size=32,replace=True)
            ga,gb = gradients(x[broad],y[broad],parameters), gradients(x[correction],y[correction],parameters)
            steps += 1
            update_hidden(parameters, m, v, ga, gb, steps)
        prediction = forward(x[valid],parameters)[0] * 200.
        losses = {str(blend):float(np.mean(np.minimum((base[valid] + blend*np.clip(prediction,-500,500)-cp[valid])**2,1000000))) for blend in (.25,.5)}
        eligible_blends = [blend for blend in losses if cohorts_pass(correction_cohorts(
            base[valid], cp[valid], float(blend) * np.clip(prediction, -500, 500)))]
        blend = min(eligible_blends, key=losses.get) if eligible_blends else min(losses, key=losses.get)
        if eligible_blends and losses[blend] < best:
            best,retained,selected_epoch,selected_blend = losses[blend],[p.copy() for p in parameters],epoch,float(blend)
        state['epochs'].append(dict(epoch=epoch, validation_capped_mse_cp=losses))
        save(OUT / 'state.json',state)
        print(f'Epoch {epoch}/16: best broad error {best:.2f} vs {baseline:.2f}',flush=True)
    np.savez_compressed(OUT / 'value.npz',weights=retained[0],bias=retained[1],output=retained[2]*200.)
    model_hash = digest(OUT / 'value.npz')
    prediction = selected_blend*np.clip(forward(x[target],retained)[0]*200.,-500,500)
    target_before = float(np.mean(abs(base[target]-cp[target])))
    target_after = float(np.mean(abs(base[target]+prediction-cp[target])))
    state.update(status='weights_frozen_before_holdout', model_sha256=model_hash, updates=steps,
        selected_epoch=selected_epoch, value_blend=selected_blend, broad_before=baseline,
        broad_after=best, target_before=target_before, target_after=target_after)
    save(OUT / 'state.json',state)
    cohorts = correction_cohorts(base[valid], cp[valid], selected_blend * np.clip(
        forward(x[valid], retained)[0] * 200., -500, 500))
    state['correction_cohorts'] = cohorts
    state['fixed_signed_head_verified'] = bool(np.array_equal(retained[2], np.asarray([.625] * 4 + [-.625] * 4, dtype=np.float32)))
    if not (best <= .99 * baseline and target_after <= .95 * target_before
            and cohorts_pass(cohorts) and selected_blend > 0):
        state.update(status='complete', passed=False, decision='reject_before_new_teacher_work',
            holdout_eligible=0, teacher_requested_nodes=0,
            finished_utc=datetime.now(timezone.utc).isoformat())
        save(OUT / 'state.json', state)
        print(json.dumps({k:v for k,v in state.items() if k not in ('epochs','holdout')}), flush=True)
        return
    teacher = game_feedback.CachedTeacher(ROOT / 'data/postgame-feedback/cache-v1',OUT)
    protected = {r['key'] for r in prep['rows']}
    prior_state = json.loads((PRIOR / 'state.json').read_text())
    protected.update(duplicate(chess.Board(r['fen'])) for r in prior_state['holdout'])
    try:
        for root in prep['heldout_roots']:
            check_stop()
            board = chess.Board(root['fen'])
            line = teacher.analyse(board,80000)
            for uci in line['pv'][:4]:
                board.push_uci(uci)
            row = dict(source_index=root['source_index'],group=root['group'],start_fen=root['fen'],
                history=[m.uci() for m in board.move_stack],fen=board.fen(),eligible=False)
            if active(board) and duplicate(board) not in protected:
                values = [teacher.analyse(board,budget) for budget in (80000,320000)]
                scores = [v['cp'] for v in values]
                eligible = all(v is not None for v in scores) and all(v['mate'] is None for v in values)
                eligible = eligible and max(map(abs,scores)) <= 1500 and abs(scores[0]-scores[1]) <= 100
                row.update(teacher=values,eligible=eligible)
                if eligible:
                    expected = sum(scores)/2
                    baseline_value = classical(*arrays(board),False)
                    residual = float(forward(features(board)[None,:768],retained)[0][0])*200.
                    actual = baseline_value + round(selected_blend*np.clip(residual,-500,500))
                    row.update(target_cp=expected,baseline_cp=int(baseline_value),prediction_cp=int(actual),
                               before_error=abs(baseline_value-expected),after_error=abs(actual-expected))
            state['holdout'].append(row)
            save(OUT / 'state.json',state)
        eligible = [r for r in state['holdout'] if r['eligible']]
        before = float(np.mean([r['before_error'] for r in eligible])) if eligible else None
        after = float(np.mean([r['after_error'] for r in eligible])) if eligible else None
        errors_before = sum(r['before_error'] >= 200 for r in eligible)
        errors_after = sum(r['after_error'] >= 200 for r in eligible)
        passed = bool(best <= .99*baseline and target_after <= .95*target_before and len(eligible) >= 12
                      and after <= before and errors_after <= errors_before and selected_blend > 0
                      and cohorts_pass(cohorts) and state['fixed_signed_head_verified'])
        state.update(status='complete',passed=passed,holdout_eligible=len(eligible),
            holdout_before=before,holdout_after=after,holdout_errors_before=errors_before,
            holdout_errors_after=errors_after,decision='needs_runtime_integration_and_short_tests' if passed else 'retain_classical_v142')
    finally:
        teacher.close()
        assert digest(OUT / 'value.npz') == model_hash
        state['teacher_requested_nodes'] = teacher.requested_nodes
        state['finished_utc'] = datetime.now(timezone.utc).isoformat()
        save(OUT / 'state.json',state)
    print(json.dumps({k:v for k,v in state.items() if k not in ('epochs','holdout')}),flush=True)


if __name__ == '__main__':
    try:
        fit(prepare())
    except BaseException as error:
        if OUT.exists():
            path = OUT / 'state.json'
            failed = json.loads(path.read_text()) if path.exists() else {}
            failed.update(status='failed', passed=False, error=repr(error),
                          finished_utc=datetime.now(timezone.utc).isoformat())
            save(path, failed)
        raise
