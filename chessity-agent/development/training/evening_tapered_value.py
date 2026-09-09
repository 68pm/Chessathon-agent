"""One bounded tapered value fit; freeze one choice before colour/generalisation gates."""
import os
for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):os.environ[name]='1'
import argparse
import json
from datetime import datetime,timezone
from pathlib import Path
import chess
import numpy as np
from scripts.evening_common import ROOT,RUN,check_stop,digest,manifest,save
from scripts.overnight_capacity import wait_for_capacity
from scripts.overnight_value_labels import duplicate,restore
from training.evening_tapered_head import features,predict,solve
from training.rule_value import arrays
from training.daytime_signed_value import correction_cohorts,cohorts_pass

OUT=RUN/'tapered-value-01'
PRIOR=ROOT/'runs/continuation-20260909/curriculum-value-02'
GM=ROOT/'runs/continuation-20260909/gm-colour-values-01'
EXPOSED=[ROOT/'runs/continuation-20260909/gm-values-01/reserved_test.json',
         ROOT/'runs/continuation-20260909/curriculum-black-check-01/state.json']

def prepare():
    check_stop();assert not OUT.exists()
    wait_for_capacity(RUN/'tapered-value-capacity-01.json',minimum_memory_mb=1400,wait_seconds=0)
    prior=json.loads((PRIOR/'preparation.json').read_text())
    assert digest(PRIOR/'dataset.npz')==prior['dataset_sha256']
    assert manifest(ROOT/prior['candidate'])==prior['candidate_files']
    assert digest(ROOT.parent/'chessity-agent.zip')==prior['selected_sha256']
    assert not (GM/'reserved_test.json').exists(),'Do not reuse consumed reservations as fresh'
    reservations=json.loads((GM/'preparation.json').read_text())
    protected=set(reservations['protected_full_game_keys'])
    rows=prior['rows'];assert len(rows)==13386
    assert not {r['key'] for r in rows}&protected
    x=[]
    for i,row in enumerate(rows):
        if i%256==0:check_stop()
        board=chess.Board(row['fen']);assert duplicate(board)==row['key'];x.append(features(board))
    with np.load(PRIOR/'dataset.npz',allow_pickle=False) as data:
        base,cp,split,kind=[data[k] for k in ('base','cp','split','kind')]
    OUT.mkdir()
    np.savez_compressed(OUT/'dataset.npz',x=np.asarray(x,dtype=np.float64),base=base,cp=cp,split=split,kind=kind)
    sources=[Path(__file__),ROOT/'training/evening_tapered_head.py',ROOT/'scripts/evening_common.py',
        ROOT/'tests/test_evening_tapered_head.py',ROOT/'docs/EVENING_TAPERED_VALUE_PLAN_20260909.md',
        PRIOR/'preparation.json',PRIOR/'dataset.npz',GM/'preparation.json',*EXPOSED]
    save(OUT/'preparation.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),prior=str(PRIOR.relative_to(ROOT)),
        candidate=prior['candidate'],candidate_files=prior['candidate_files'],selected_sha256=prior['selected_sha256'],
        rows=len(rows),dataset_sha256=digest(OUT/'dataset.npz'),protected_full_game_keys=sorted(protected),
        sources={str(p):digest(p) for p in sources},penalties=[10,100,1000],blends=[.25,.5,1.],
        coefficient_cap=80.,output_cap=250.,target_cap=500.,architecture='768-weight symmetric tapered linear position head'))
    print('Prepared13386 labelled rows with frozen whole-game exclusions',flush=True)

def verify(prep):
    assert all(digest(Path(p))==h for p,h in prep['sources'].items())
    assert manifest(ROOT/prep['candidate'])==prep['candidate_files']
    assert digest(OUT/'dataset.npz')==prep['dataset_sha256']

def fit():
    check_stop();prep=json.loads((OUT/'preparation.json').read_text());verify(prep)
    assert not (OUT/'state.json').exists()
    wait_for_capacity(OUT/'fit-capacity.json',minimum_memory_mb=1400,wait_seconds=0)
    with np.load(OUT/'dataset.npz',allow_pickle=False) as d:x,base,cp,split,kind=[d[k] for k in ('x','base','cp','split','kind')]
    train=split==0;valid=split==1;recent=kind=='recent';gm=kind=='gm'
    target=np.clip(cp-base,-500,500);row_weights=np.where(recent,4.,np.where(gm,2.,1.))
    before=float(np.mean(np.minimum((base[valid]-cp[valid])**2,1000000)))
    state=dict(status='fitting',passed=False,broad_before=before,grid=[])
    save(OUT/'state.json',state)
    candidates=[]
    for penalty in prep['penalties']:
        check_stop()
        weights=np.clip(solve(x[train],target[train],row_weights[train],penalty),-80,80).astype(np.float32)
        for blend in prep['blends']:
            correction=predict(x,weights,blend)
            mse=float(np.mean(np.minimum((base[valid]+correction[valid]-cp[valid])**2,1000000)))
            record=dict(penalty=penalty,blend=blend,broad_mse=mse)
            state['grid'].append(record);candidates.append((mse,penalty,blend,weights.copy()))
        save(OUT/'state.json',state)
    mse,penalty,blend,weights=min(candidates,key=lambda r:(r[0],r[1],r[2]))
    np.savez_compressed(OUT/'value.npz',weights=weights.reshape(2,6,64),blend=np.asarray(blend,dtype=np.float32))
    correction=predict(x,weights,blend)
    cohorts=correction_cohorts(base[valid],cp[valid],correction[valid])
    target_metrics={label:dict(n=int(mask.sum()),before_mae=float(np.mean(abs(base[mask]-cp[mask]))),
        after_mae=float(np.mean(abs(base[mask]+correction[mask]-cp[mask])))) for label,mask in (('recent',recent),('gm',gm))}
    passed=mse<=.95*before and cohorts_pass(cohorts) and all(r['after_mae']<=r['before_mae'] for r in target_metrics.values())
    state.update(status='weights_frozen_before_colour_checks' if passed else 'complete',passed=False,
        development_fit_passed=bool(passed),selected_penalty=penalty,value_blend=blend,broad_after=mse,
        correction_cohorts=cohorts,target_metrics=target_metrics,model_sha256=digest(OUT/'value.npz'),
        decision='needs_exposed_and_fresh_colour_checks' if passed else 'reject_development_fit',
        finished_utc=datetime.now(timezone.utc).isoformat())
    save(OUT/'state.json',state)
    print(json.dumps({k:v for k,v in state.items() if k!='grid'}),flush=True)

def evaluate_labels(labels,output):
    from training.continuation_curriculum_value import classical
    prep=json.loads((OUT/'preparation.json').read_text());verify(prep)
    state=json.loads((OUT/'state.json').read_text());assert state['development_fit_passed']
    assert digest(OUT/'value.npz')==state['model_sha256'];assert not output.exists()
    prior=json.loads((PRIOR/'preparation.json').read_text());used={r['key'] for r in prior['rows']}
    fn=classical(ROOT/prep['candidate'])
    with np.load(OUT/'value.npz',allow_pickle=False) as model:weights=model['weights'];blend=float(model['blend'])
    rows=[]
    for row in labels:
        check_stop()
        if not row['eligible']:continue
        board=restore(row);assert duplicate(board) not in used
        before=float(fn(*arrays(board),False))
        after=before+float(predict(features(board),weights,blend));target=row['target_stm_cp']
        rows.append(dict(id=row['id'],group=row['group'],white=board.turn,target_stm_cp=target,
            before_cp=before,after_cp=after,before_error_cp=abs(before-target),after_error_cp=abs(after-target)))
    cohorts={}
    for label,white in (('white',True),('black',False)):
        chosen=[r for r in rows if r['white']==white]
        a=float(np.mean([r['before_error_cp'] for r in chosen]));b=float(np.mean([r['after_error_cp'] for r in chosen]))
        ma=sum(r['before_error_cp']>=200 for r in chosen);mb=sum(r['after_error_cp']>=200 for r in chosen)
        cohorts[label]=dict(n=len(chosen),before_mae_cp=a,after_mae_cp=b,major_before=ma,major_after=mb,
            passed=bool(len(chosen)>=6 and b<=a and mb<=ma))
    result=dict(status='complete',passed=all(r['passed'] for r in cohorts.values()),cohorts=cohorts,
        model_sha256=state['model_sha256'],rows=rows)
    save(output,result);return result

def exposed():
    state=json.loads((OUT/'state.json').read_text());assert state['status']=='weights_frozen_before_colour_checks'
    labels=[r for p in EXPOSED for r in json.loads(p.read_text())['rows']]
    result=evaluate_labels(labels,OUT/'exposed-development.json')
    state.update(status='weights_frozen_before_reserved_labels' if result['passed'] else 'complete',
        decision='needs_fresh_reserved_colours' if result['passed'] else 'reject_exposed_colours',passed=False)
    save(OUT/'state.json',state);print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--mode',choices=('prepare','fit','exposed'),required=True)
    args=parser.parse_args()
    try:globals()[args.mode]()
    except BaseException as error:
        if OUT.exists():
            path=OUT/'state.json';state=json.loads(path.read_text()) if path.exists() else {}
            state.update(status='failed',passed=False,error=repr(error));save(path,state)
        raise
