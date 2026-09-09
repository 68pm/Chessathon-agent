"""Same declared fit with actual Black GM labels and separate colour gates."""
import json
from datetime import datetime,timezone
from pathlib import Path

import chess
import numpy as np

from training import continuation_curriculum_value as base
from scripts.continuation_common import ROOT,RUN,check_stop,digest,manifest,save
from scripts.continuation_colour_labels import OUT as GM
from scripts.overnight_value_labels import duplicate,restore
from scripts.overnight_capacity import wait_for_capacity
from training.residual_value import forward
from training.rule_value import features,arrays

OUT=RUN/'curriculum-value-02'
PRIOR=RUN/'curriculum-value-01'


def prepare():
    check_stop();assert not OUT.exists()
    wait_for_capacity(RUN/'curriculum-value-capacity-02.json',minimum_memory_mb=1400,wait_seconds=0)
    prep=json.loads((PRIOR/'preparation.json').read_text())
    assert digest(PRIOR/'dataset.npz')==prep['dataset_sha256']
    assert manifest(ROOT/prep['candidate'])==prep['candidate_files']
    gm_prep=json.loads((GM/'preparation.json').read_text());labels=json.loads((GM/'train.json').read_text())
    assert labels['status']=='complete'
    protected=set(gm_prep['protected_full_game_keys'])
    keep=[i for i,r in enumerate(prep['rows']) if r['key'] not in protected]
    rows=[dict(prep['rows'][i]) for i in keep];used={r['key'] for r in rows}|protected
    new=[]
    for r in labels['rows']:
        if not r['eligible'] or r['key'] in used:continue
        board=restore(r);assert board.turn==chess.BLACK
        used.add(r['key'])
        item=dict(fen=r['fen'],cp=r['target_stm_cp'],split=0,kind='gm',key=r['key'],
            group=r['group'],source_id=r['id'],phase=base.phase(board),
            start_fen=r['start_fen'],history=r['history'],new_actual_black=True)
        rows.append(item);new.append(item)
    assert len(new)>=24
    assert not ({r['key'] for r in rows if r['split']==0}&{r['key'] for r in rows if r['split']==1})
    assert not ({r['key'] for r in rows}&protected)
    fn=base.classical(ROOT/prep['candidate'])
    with np.load(PRIOR/'dataset.npz',allow_pickle=False) as data:
        x=data['x'][keep];oldbase=data['base'][keep]
    x=np.concatenate([x,np.asarray([features(chess.Board(r['fen']))[:768] for r in new],dtype=np.float32)])
    classical=np.concatenate([oldbase,np.asarray([fn(*arrays(chess.Board(r['fen'])),False) for r in new],dtype=np.float32)])
    cp=np.asarray([r['cp'] for r in rows],dtype=np.float32)
    OUT.mkdir()
    np.savez_compressed(OUT/'dataset.npz',x=x,base=classical,cp=cp,y=np.clip((cp-classical)/200.,-2.5,2.5),
        split=[r['split'] for r in rows],kind=[r['kind'] for r in rows],phase=[r['phase'] for r in rows])
    sources=[Path(__file__),Path(base.__file__),PRIOR/'preparation.json',PRIOR/'dataset.npz',
        GM/'preparation.json',GM/'train.json',ROOT/'docs/CONTINUATION_COLOUR_COVERAGE_PLAN_20260909.md']
    save(OUT/'preparation.json',dict(rows=rows,candidate=prep['candidate'],candidate_files=prep['candidate_files'],
        selected_sha256=prep['selected_sha256'],seed=base.SEED,new_actual_black=len(new),
        removed_original_rows=len(prep['rows'])-len(keep),sources={str(p):digest(p) for p in sources},
        dataset_sha256=digest(OUT/'dataset.npz'),architecture=prep['architecture'],
        protected_full_game_keys=sorted(protected),
        scope='Same fit hyperparameters, added independently labelled actual Black-to-move GM targets. '
              'Earlier reservations are exposed development. New reservations are three unused Italian games.'))
    print(json.dumps(dict(rows=len(rows),new_actual_black=len(new),removed=len(prep['rows'])-len(keep))),flush=True)


def evaluate(reserved):
    check_stop()
    state=json.loads((OUT/'state.json').read_text())
    assert state['status']=='weights_frozen_before_reserved_labels'
    assert digest(OUT/'value.npz')==state['model_sha256']
    prep=json.loads((OUT/'preparation.json').read_text());used={r['key'] for r in prep['rows']}
    if reserved:
        doc=json.loads((GM/'reserved_test.json').read_text())
        assert doc['status']=='complete' and doc['model_sha256']==state['model_sha256']
        labels=doc['rows']
    else:
        docs=[RUN/'gm-values-01/reserved_test.json',RUN/'curriculum-black-check-01/state.json']
        labels=[r for path in docs for r in json.loads(path.read_text())['rows']]
    fn=base.classical(ROOT/prep['candidate'])
    with np.load(OUT/'value.npz',allow_pickle=False) as data:p=[data['weights'],data['bias'],data['output']/200.]
    rows=[]
    for r in labels:
        if not r['eligible']:continue
        board=restore(r);assert duplicate(board) not in used
        before=float(fn(*arrays(board),False));truth=r['target_stm_cp']
        after=before+state['value_blend']*float(np.clip(forward(features(board)[None,:768],p)[0][0]*200.,-500,500))
        rows.append(dict(id=r['id'],group=r['group'],white=board.turn,fen=r['fen'],target_stm_cp=truth,
            before_cp=before,after_cp=after,before_error_cp=abs(before-truth),after_error_cp=abs(after-truth)))
    cohorts={}
    for label,white in (('white',True),('black',False)):
        selected=[r for r in rows if r['white']==white]
        before=float(np.mean([r['before_error_cp'] for r in selected])) if selected else None
        after=float(np.mean([r['after_error_cp'] for r in selected])) if selected else None
        major_before=sum(r['before_error_cp']>=200 for r in selected)
        major_after=sum(r['after_error_cp']>=200 for r in selected)
        cohorts[label]=dict(n=len(selected),before_mae_cp=before,after_mae_cp=after,
            major_before=major_before,major_after=major_after,
            passed=bool(len(selected)>=6 and after<=before and major_after<=major_before))
    passed=all(r['passed'] for r in cohorts.values())
    result=dict(status='complete',passed=passed,cohorts=cohorts,rows=rows,
        model_sha256=state['model_sha256'],scope='fresh reserved Italian positions' if reserved else 'exposed colour development')
    save(OUT/('reserved-evaluation.json' if reserved else 'exposed-development.json'),result)
    if reserved or not passed:
        state.update(status='complete',passed=bool(reserved and passed),
            decision=('eligible_for_runtime_quality_trial' if passed else 'reject_after_reserved_colours') if reserved else 'reject_exposed_colour_development',
            finished_utc=datetime.now(timezone.utc).isoformat())
        save(OUT/'state.json',state)
    assert digest(OUT/'value.npz')==state['model_sha256']
    print(json.dumps({k:v for k,v in result.items() if k!='rows'}),flush=True)


if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['prepare','fit','exposed','reserved'],required=True)
    mode=parser.parse_args().mode
    try:
        if mode=='prepare':prepare()
        elif mode=='fit':base.OUT=OUT;base.fit()
        else:evaluate(mode=='reserved')
    except BaseException as error:
        if OUT.exists():
            path=OUT/'state.json';state=json.loads(path.read_text()) if path.exists() else {}
            state.update(status='failed',passed=False,error=repr(error));save(path,state)
        raise
