"""A bounded perspective-difference residual fit with fresh descendant evaluation."""
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
from scripts.overnight_value_labels import duplicate
from training.daytime_antisymmetric import forward, gradients
from training.daytime_signed_value import (
    cohorts_pass,
    correction_cohorts,
    signed_parameters,
    update_hidden,
)
from training.daytime_small_value import active
from training.rule_value import arrays, features

OUT = RUN / 'antisymmetric-value-02'
PRIOR = RUN / 'balanced-value-01'
DESC = RUN / 'student-descendants-01'
SEED = 2026090912
SOURCE = ROOT / 'runs/unattended-20260905-away/data-300000/dataset.npz'


def write_model(path, parameters):
    np.savez_compressed(path, weights=parameters[0], bias=parameters[1], output=parameters[2]*200.)


def load_classical(candidate):
    path = candidate / 'engine/compiled_core.py'
    spec = importlib.util.spec_from_file_location('antisymmetric_exact55_classical', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.classical


def prepare():
    import shutil

    check_stop()
    assert not OUT.exists(), 'Preserve every consumed trial.'
    capacity = RUN / 'antisymmetric-value-capacity-02.json'
    assert not capacity.exists()
    wait_for_capacity(capacity, minimum_memory_mb=1400, wait_seconds=120)
    selected_path = ROOT.parent / 'chessity-agent-version.json'
    selected = json.loads(selected_path.read_text())
    assert selected['version'] == 'v1.55'
    assert selected['sha256'] == digest(ROOT.parent / 'chessity-agent.zip')
    candidate = ROOT / selected['source_version']
    prior = json.loads((PRIOR / 'preparation.json').read_text())
    prior_state = json.loads((PRIOR / 'state.json').read_text())
    assert prior_state['status'] == 'complete' and not prior_state['passed']
    assert prior_state['decision'] == 'reject_after_holdout'
    assert digest(PRIOR/'dataset.npz') == prior['dataset_sha256']
    assert manifest(candidate) == prior['candidate_files']
    assert all(digest(Path(p)) == h for p,h in prior['sources'].items())
    rows = prior['rows']
    assert len(rows) == 13297 and sum(r['targeted'] for r in rows) == 97
    protected = set(prior['protected_keys']) | {r['key'] for r in rows}
    protected.update(duplicate(chess.Board(r['fen'])) for r in prior_state['holdout'])
    prior_preparations = [RUN/name/'preparation.json' for name in
        ('small-value-01','signed-value-01','balanced-value-01')]
    excluded_groups = {r['group'] for r in rows if r['targeted']}
    for path in prior_preparations:
        old = json.loads(path.read_text())
        excluded_groups.update(r['group'] for r in old['heldout_roots'])
        protected.update(duplicate(chess.Board(r['fen'])) for r in old['heldout_roots'])
    heldout, pools = [], {}
    rng = np.random.default_rng(SEED)
    with np.load(SOURCE,allow_pickle=False) as data:
        fens, cp, split, groups = [data[k] for k in ('fen','cp','split','group')]
    assert all(not (set(groups[split==a]) & set(groups[split==b]))
        for a,b in ((0,1),(0,2),(1,2)))
    indices = np.flatnonzero((split==2) & np.isfinite(cp) & (abs(cp)<=1500))
    rng.shuffle(indices)
    for offset,index in enumerate(indices):
        if offset % 128 == 0:
            check_stop()
        group = str(groups[index])
        if group in excluded_groups or len(pools.get(group,[])) >= 3:
            continue
        board = chess.Board(str(fens[index]))
        key = duplicate(board)
        if key in protected or not active(board):
            continue
        pools.setdefault(group,[]).append(dict(fen=board.fen(), cp=float(cp[index]), split=2,
            source_index=int(index), group=group, key=key))
        protected.add(key)
    group_order = list(pools)
    rng.shuffle(group_order)
    for round_index in range(3):
        for group in group_order:
            if len(pools[group]) > round_index:
                heldout.append(pools[group][round_index])
                if len(heldout)==24:
                    break
        if len(heldout)==24:
            break
    assert len(heldout)==24, 'Insufficient new reservation groups; do not reuse exposed data.'
    assert len({r['group'] for r in heldout}) >= 8
    assert all(sum(r['group']==g for r in heldout)<=3 for g in group_order)
    assert not ({r['group'] for r in heldout} & excluded_groups)
    OUT.mkdir()
    shutil.copyfile(PRIOR/'dataset.npz',OUT/'dataset.npz')
    assert digest(OUT/'dataset.npz') == prior['dataset_sha256']
    sources = [Path(__file__), selected_path, SOURCE, *prior_preparations,
        PRIOR/'state.json', PRIOR/'dataset.npz', DESC/'teacher.json',
        ROOT/'docs/DAYTIME_ANTISYMMETRIC_VALUE_PLAN_20260909.md',
        ROOT/'docs/DAYTIME_ANTISYMMETRIC_RESERVATIONS_20260909.md',
        ROOT/'training/daytime_antisymmetric_value.py',
        ROOT/'training/daytime_antisymmetric.py', ROOT/'tests/test_daytime_antisymmetric.py',
        ROOT/'training/daytime_signed_value.py', ROOT/'training/daytime_small_value.py',
        ROOT/'training/rule_value.py', ROOT/'training/game_feedback.py',
        ROOT/'scripts/daytime_common.py']
    save(OUT/'preparation.json',dict(rows=rows, heldout_roots=heldout, seed=SEED,
        protected_keys=sorted(protected), excluded_holdout_groups=sorted(excluded_groups),
        selected_version=selected['version'], selected_sha256=selected['sha256'],
        candidate=str(candidate.relative_to(ROOT)), candidate_files=manifest(candidate),
        sources={str(p):digest(p) for p in sources}, dataset_sha256=digest(OUT/'dataset.npz'),
        architecture='Half difference of two relative 768/8 clipped-ReLU perspectives, fixed signed readouts',
        epochs=16, broad_batch=[112,112,32], targeted_batch=[16,16], gradient_mix=[.8,.2],
        teacher_limit=11520000, automatic_runtime_integration=False,
        scope='Same training and development rows as balanced-value-01; fresh split2 reservations. '
            'Public target game lacks ECO: semantic opening overlap is uncontrolled. No synthetic turn-reversed labels.'))
    return load_classical(candidate)


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
