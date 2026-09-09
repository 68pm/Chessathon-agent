"""A bounded signed-head fit with balanced correction sampling and saved epochs."""
import os

for _name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[_name] = '1'

import importlib.util
import json
from datetime import datetime, timezone
from pathlib import Path

import chess
import numpy as np

from scripts.daytime_common import ROOT, RUN, check_stop, digest, manifest, save
from scripts.overnight_capacity import wait_for_capacity
from scripts.overnight_value_labels import duplicate, restore
from training.daytime_signed_value import (
    cohorts_pass,
    correction_cohorts,
    signed_parameters,
    update_hidden,
)
from training.daytime_small_value import active
from training.residual_value import forward, gradients
from training.rule_value import arrays, features

OUT = RUN / 'balanced-value-01'
PRIOR = RUN / 'signed-value-01'
DESC = RUN / 'student-descendants-01'
SEED = 2026090911


def write_model(path, parameters):
    np.savez_compressed(path, weights=parameters[0], bias=parameters[1], output=parameters[2]*200.)


def load_classical(candidate):
    path = candidate / 'engine/compiled_core.py'
    spec = importlib.util.spec_from_file_location('balanced_exact55_classical', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.classical


def prepare():
    check_stop()
    assert not OUT.exists(), 'Preserve every consumed trial.'
    capacity = RUN / 'balanced-value-capacity-01.json'
    assert not capacity.exists()
    wait_for_capacity(capacity, minimum_memory_mb=1400, wait_seconds=120)
    selected_path = ROOT.parent / 'chessity-agent-version.json'
    selected = json.loads(selected_path.read_text())
    assert selected['version'] == 'v1.55'
    assert selected['sha256'] == digest(ROOT.parent / 'chessity-agent.zip')
    candidate = ROOT / selected['source_version']
    classical = load_classical(candidate)
    prior = json.loads((PRIOR / 'preparation.json').read_text())
    prior_state = json.loads((PRIOR / 'state.json').read_text())
    assert prior_state['status'] == 'complete' and not prior_state['passed'] and not prior_state['holdout']
    teacher = json.loads((DESC / 'teacher.json').read_text())
    assert teacher['status'] == 'complete'
    assert teacher['student_sha256'] == digest(DESC / 'student.json')
    targets = {}
    conflicts, exclusions = set(), []
    for row in prior['rows']:
        if row['targeted']:
            key = duplicate(chess.Board(row['fen']))
            assert key not in targets
            targets[key] = dict(row, new_descendant=False)
    for leaf in teacher['rows']:
        board = restore(leaf)
        q = leaf.get('quiescence', {})
        if not (leaf['eligible'] and active(board) and q.get('complete')
                and q.get('score_stm_cp') is not None
                and abs(q['score_stm_cp']-leaf['static_stm_cp']) <= 75):
            exclusions.append(leaf['id'])
            continue
        key = duplicate(board)
        row = dict(fen=leaf['fen'], cp=leaf['target_stm_cp'], split=0, targeted=True,
            key=key, source_id=leaf['id'], root_id=leaf['root_id'],
            start_fen=leaf['start_fen'], history=leaf['history'], new_descendant=True,
            group='public-round76' if leaf['root_id'].startswith('field-') else 'D65')
        if key in targets:
            if abs(targets[key]['cp']-row['cp']) > 100:
                conflicts.add(key)
            elif not targets[key]['new_descendant']:
                targets[key] = row
        else:
            targets[key] = row
    targets = {k:v for k,v in targets.items() if k not in conflicts}
    assert sum(r['new_descendant'] for r in targets.values()) >= 16
    protected = set(targets) | {duplicate(restore(r)) for r in teacher['rows']}
    old = json.loads((RUN / 'small-value-01/state.json').read_text())
    old_prep = json.loads((RUN / 'small-value-01/preparation.json').read_text())
    protected.update(duplicate(chess.Board(r['fen'])) for r in old['holdout'])
    protected.update(duplicate(chess.Board(r['fen'])) for r in old_prep['heldout_roots'])
    heldout = prior['heldout_roots']
    assert len(heldout) == 24
    protected.update(duplicate(chess.Board(r['fen'])) for r in heldout)
    rows = [dict(r, new_descendant=False) for r in prior['rows']
            if not r['targeted'] and r['key'] not in protected]
    rows.extend(targets.values())
    assert not ({r['key'] for r in rows if r['split'] == 0}
                & {r['key'] for r in rows if r['split'] == 1})
    assert all(r['group'] not in ('C09','D28','D65') for r in rows if r['split'] == 1)
    x, base = [], []
    for i, row in enumerate(rows):
        if i % 256 == 0:
            check_stop()
        board = chess.Board(row['fen'])
        x.append(features(board)[:768])
        base.append(classical(*arrays(board), False))
    base = np.asarray(base, dtype=np.float32)
    cp = np.asarray([r['cp'] for r in rows], dtype=np.float32)
    OUT.mkdir()
    np.savez_compressed(OUT / 'dataset.npz', x=np.asarray(x, dtype=np.float32), base=base, cp=cp,
        y=np.clip((cp-base)/200., -2.5, 2.5), split=[r['split'] for r in rows],
        targeted=[r['targeted'] for r in rows], new_descendant=[r['new_descendant'] for r in rows])
    sources = [Path(__file__), selected_path, PRIOR/'preparation.json', PRIOR/'state.json',
        DESC/'teacher.json', DESC/'student.json', DESC/'preparation.json',
        RUN/'small-value-01/state.json', RUN/'small-value-01/preparation.json',
        ROOT/'docs/DAYTIME_BALANCED_VALUE_PLAN_20260909.md',
        ROOT/'training/daytime_signed_value.py', ROOT/'training/daytime_small_value.py',
        ROOT/'training/residual_value.py', ROOT/'training/rule_value.py',
        ROOT/'training/game_feedback.py', ROOT/'scripts/daytime_common.py']
    save(OUT / 'preparation.json', dict(rows=rows, heldout_roots=heldout, seed=SEED,
        protected_keys=sorted(protected), excluded_new_ids=exclusions, conflicting_keys=sorted(conflicts),
        selected_version=selected['version'], selected_sha256=selected['sha256'],
        candidate=str(candidate.relative_to(ROOT)), candidate_files=manifest(candidate),
        sources={str(p):digest(p) for p in sources}, dataset_sha256=digest(OUT/'dataset.npz'),
        architecture='768/8 clipped ReLU with fixed four +125/four -125 cp heads',
        epochs=16, broad_batch=[112,112,32], targeted_batch=[16,16], gradient_mix=[.8,.2],
        teacher_limit=11520000, automatic_runtime_integration=False,
        scope='Reused development validation; unused split2 reservations evaluated only after weight freeze. '
              'Public target game lacks ECO: semantic overlap with broad opening groups is uncontrolled.'))
    return classical


def fit(classical):
    from training import game_feedback

    game_feedback.stop_check = check_stop
    prep = json.loads((OUT/'preparation.json').read_text())
    assert all(digest(Path(p)) == h for p,h in prep['sources'].items())
    assert not (OUT/'state.json').exists()
    with np.load(OUT/'dataset.npz', allow_pickle=False) as data:
        x, base, cp, y, split, targeted, new = [data[k] for k in
            ('x','base','cp','y','split','targeted','new_descendant')]
    train = np.flatnonzero((split == 0) & ~targeted)
    valid, target, recent = np.flatnonzero(split == 1), np.flatnonzero(targeted), np.flatnonzero(new)
    delta = cp-base
    broad_pools = [train[delta[train] <= -25], train[delta[train] >= 25], train[abs(delta[train]) < 25]]
    target_pools = [target[delta[target] <= -25], target[delta[target] >= 25]]
    assert all(len(pool) >= 16 for pool in broad_pools) and all(len(pool) >= 5 for pool in target_pools)
    baseline = float(np.mean(np.minimum((base[valid]-cp[valid])**2, 1000000)))
    target_before = float(np.mean(abs(base[target]-cp[target])))
    recent_before = float(np.mean(abs(base[recent]-cp[recent])))
    rng = np.random.default_rng(SEED)
    parameters = signed_parameters(rng)
    m, v = [np.zeros_like(p) for p in parameters], [np.zeros_like(p) for p in parameters]
    best, selected_epoch, selected_blend, steps, retained = baseline, 0, 0., 0, None
    state = dict(status='training', passed=False, epochs=[], holdout=[],
        broad_before=baseline, target_before=target_before, new_descendant_before=recent_before)
    save(OUT/'state.json', state)
    (OUT/'epochs').mkdir()
    for epoch in range(1,17):
        for _ in range((len(train)+255)//256):
            check_stop()
            broad = np.concatenate([rng.choice(pool,size=n,replace=True)
                for pool,n in zip(broad_pools,(112,112,32))])
            correction = np.concatenate([rng.choice(pool,size=16,replace=True) for pool in target_pools])
            steps += 1
            update_hidden(parameters,m,v,gradients(x[broad],y[broad],parameters),
                gradients(x[correction],y[correction],parameters),steps)
        raw = np.clip(forward(x,parameters)[0]*200.,-500,500)
        metrics = {}
        for blend in (.25,.5):
            residual = blend*raw
            mse = float(np.mean(np.minimum((base[valid]+residual[valid]-cp[valid])**2,1000000)))
            cohorts = correction_cohorts(base[valid],cp[valid],residual[valid])
            target_after = float(np.mean(abs(base[target]+residual[target]-cp[target])))
            recent_after = float(np.mean(abs(base[recent]+residual[recent]-cp[recent])))
            eligible = (mse <= .99*baseline and cohorts_pass(cohorts)
                and target_after <= .95*target_before and recent_after <= .95*recent_before)
            metrics[str(blend)] = dict(capped_mse_cp=mse, correction_cohorts=cohorts,
                target_mae_cp=target_after, new_descendant_mae_cp=recent_after, eligible=eligible)
            if eligible and mse < best:
                best, selected_epoch, selected_blend = mse, epoch, blend
                retained = [p.copy() for p in parameters]
        checkpoint = OUT/'epochs'/f'epoch-{epoch:02d}.npz'
        write_model(checkpoint,parameters)
        state['epochs'].append(dict(epoch=epoch, metrics=metrics, checkpoint_sha256=digest(checkpoint)))
        save(OUT/'state.json', state)
        print(f'Epoch {epoch}/16: selected {selected_epoch}, broad {best:.2f} vs {baseline:.2f}',flush=True)
    state.update(updates=steps, selected_epoch=selected_epoch, value_blend=selected_blend,
        broad_after=best)
    if retained is None:
        state.update(status='complete', decision='reject_before_teacher_work', teacher_requested_nodes=0,
            finished_utc=datetime.now(timezone.utc).isoformat())
        save(OUT/'state.json',state)
        return
    write_model(OUT/'value.npz',retained)
    state.update(status='weights_frozen_before_holdout', model_sha256=digest(OUT/'value.npz'))
    save(OUT/'state.json',state)
    protected = set(prep['protected_keys']) | {r['key'] for r in prep['rows']}
    teacher = game_feedback.CachedTeacher(ROOT/'data/postgame-feedback/cache-v1',OUT)
    try:
        for root in prep['heldout_roots']:
            check_stop()
            board = chess.Board(root['fen'])
            root_label = teacher.analyse(board,80000)
            line = root_label['pv'][:4]
            for uci in line:
                board.push_uci(uci)
            row = dict(group=root['group'], source_index=root['source_index'], start_fen=root['fen'],
                history=[m.uci() for m in board.move_stack], fen=board.fen(), eligible=False,
                root_label=root_label, fresh_descendant=len(line)==4)
            if len(line)==4 and active(board) and duplicate(board) not in protected:
                labels = [teacher.analyse(board,budget) for budget in (80000,320000)]
                cp_pair = [r['cp'] for r in labels]
                row['teacher'] = labels
                if (all(v is not None for v in cp_pair) and all(r['mate'] is None for r in labels)
                        and max(map(abs,cp_pair)) <= 1500 and abs(cp_pair[0]-cp_pair[1]) <= 100):
                    before = float(classical(*arrays(board),False))
                    residual = selected_blend*float(np.clip(forward(features(board)[None,:768],retained)[0][0]*200.,-500,500))
                    truth = sum(cp_pair)/2
                    row.update(eligible=True, target_stm_cp=truth, before_cp=before, after_cp=before+residual,
                        before_error_cp=abs(before-truth), after_error_cp=abs(before+residual-truth))
                protected.add(duplicate(board))
            state['holdout'].append(row)
            save(OUT/'state.json',state)
        eligible = [r for r in state['holdout'] if r['eligible']]
        before = float(np.mean([r['before_error_cp'] for r in eligible])) if eligible else None
        after = float(np.mean([r['after_error_cp'] for r in eligible])) if eligible else None
        major_before = sum(r['before_error_cp'] >= 200 for r in eligible)
        major_after = sum(r['after_error_cp'] >= 200 for r in eligible)
        passed = len(eligible)>=12 and after<=before and major_after<=major_before
        assert digest(OUT/'value.npz') == state['model_sha256']
        assert manifest(ROOT/prep['candidate']) == prep['candidate_files']
        state.update(status='complete', passed=passed, holdout_eligible=len(eligible),
            holdout_before_mae_cp=before, holdout_after_mae_cp=after,
            holdout_major_before=major_before, holdout_major_after=major_after,
            decision='eligible_for_runtime_quality_trial' if passed else 'reject_after_holdout')
    finally:
        teacher.close()
        state.update(teacher_requested_nodes=teacher.requested_nodes,
            finished_utc=datetime.now(timezone.utc).isoformat())
        save(OUT/'state.json',state)
    assert teacher.requested_nodes <= prep['teacher_limit']


if __name__ == '__main__':
    try:
        fit(prepare())
    except BaseException as error:
        if OUT.exists():
            state_path = OUT/'state.json'
            state = json.loads(state_path.read_text()) if state_path.exists() else {}
            state.update(status='failed', passed=False, error=repr(error),
                finished_utc=datetime.now(timezone.utc).isoformat())
            save(state_path,state)
        raise
