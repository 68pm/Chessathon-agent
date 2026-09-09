"""A bounded original position-value fit including recent errors and quiet endings."""
import os
for _name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[_name]='1'

import argparse
import importlib.util
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import chess
import numpy as np

from scripts.continuation_common import ROOT, RUN, check_stop, digest, manifest, save
from scripts.continuation_gm_labels import active
from scripts.overnight_capacity import wait_for_capacity
from scripts.overnight_value_labels import duplicate, restore
from training.daytime_signed_value import correction_cohorts, cohorts_pass, update_hidden
from training.residual_value import forward, gradients
from training.rule_value import arrays, features

OUT=RUN/'curriculum-value-01'
GM=RUN/'gm-values-01'
DESC=RUN/'student-descendants-01/teacher.json'
SOURCE=ROOT/'runs/unattended-20260905-away/data-300000/dataset.npz'
SEED=2026090917


def phase(board):
    return sum(len(board.pieces(p,c))*v for p,v in ((2,1),(3,1),(4,2),(5,4)) for c in (True,False))


def classical(candidate):
    spec=importlib.util.spec_from_file_location('continuation56_classical_value',candidate/'engine/compiled_core.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.classical


def write_model(path, p):
    np.savez_compressed(path,weights=p[0],bias=p[1],output=p[2]*200.)


def prepare():
    check_stop()
    assert not OUT.exists(),'Preserve consumed fits.'
    wait_for_capacity(RUN/'curriculum-value-capacity-01.json',minimum_memory_mb=1400,wait_seconds=0)
    selected_path=ROOT.parent/'chessity-agent-version.json'
    selected=json.loads(selected_path.read_text())
    assert selected['version']=='v1.56' and selected['sha256']==digest(ROOT.parent/'chessity-agent.zip')
    candidate=ROOT/selected['source_version']
    fn=classical(candidate)
    gm_prep=json.loads((GM/'preparation.json').read_text())
    gm=json.loads((GM/'train.json').read_text())
    descendants=json.loads(DESC.read_text())
    assert gm['status']==descendants['status']=='complete'
    protected=set(gm_prep['reserved_full_game_keys'])
    targets, conflicts, exclusions={},set(),[]
    for kind, collection in (('recent',descendants['rows']),('gm',gm['rows'])):
        for item in collection:
            board=restore(item)
            key=duplicate(board)
            q=item.get('quiescence',{})
            good=(item['eligible'] and active(board) and key not in protected)
            if kind=='recent':
                good=good and q.get('complete') and q.get('score_stm_cp') is not None and abs(q['score_stm_cp']-item['static_stm_cp'])<=75
            if not good:
                exclusions.append(dict(id=item['id'],kind=kind))
                continue
            row=dict(fen=board.fen(),cp=item['target_stm_cp'],split=0,kind=kind,key=key,
                source_id=item['id'],group=item.get('group',item.get('root_id')),phase=phase(board),
                start_fen=item['start_fen'],history=item['history'])
            if key in targets and abs(targets[key]['cp']-row['cp'])>100:conflicts.add(key)
            elif key not in targets:targets[key]=row
    targets={k:v for k,v in targets.items() if k not in conflicts}
    assert sum(r['kind']=='recent' for r in targets.values())>=24
    assert sum(r['kind']=='gm' for r in targets.values())>=24
    used=protected|set(targets)
    rng=np.random.default_rng(SEED)
    with np.load(SOURCE,allow_pickle=False) as data:
        fens,cp,split,groups=[data[k] for k in ('fen','cp','split','group')]
    rows=[]
    for partition,limit,end_limit in ((1,1200,300),(0,12000,3000)):
        indices=np.flatnonzero((split==partition)&np.isfinite(cp)&(abs(cp)<=1500))
        rng.shuffle(indices)
        pools={'endgame':[],'other':[]}
        for i in indices:
            if i%256==0:check_stop()
            board=chess.Board(str(fens[i]))
            if not active(board):continue
            key=duplicate(board)
            if key in used:continue
            ph=phase(board)
            pool='endgame' if ph<=8 else 'other'
            cap=end_limit if pool=='endgame' else limit-end_limit
            if len(pools[pool])>=cap:continue
            used.add(key)
            pools[pool].append(dict(fen=board.fen(),cp=float(cp[i]),split=partition,kind='broad',
                key=key,source_index=int(i),group=str(groups[i]),phase=ph))
            if sum(map(len,pools.values()))==limit:break
        assert len(pools['endgame'])>=min(100,end_limit)
        assert sum(map(len,pools.values()))>=.9*limit
        rows.extend(pools['endgame']+pools['other'])
    rows.extend(targets.values())
    assert not ({r['key'] for r in rows if r['split']==0}&{r['key'] for r in rows if r['split']==1})
    assert not ({r['key'] for r in rows}&protected)
    x,base=[],[]
    for i,r in enumerate(rows):
        if i%256==0:check_stop()
        board=chess.Board(r['fen'])
        x.append(features(board)[:768]);base.append(fn(*arrays(board),False))
    base=np.asarray(base,dtype=np.float32)
    cp=np.asarray([r['cp'] for r in rows],dtype=np.float32)
    OUT.mkdir()
    np.savez_compressed(OUT/'dataset.npz',x=np.asarray(x,dtype=np.float32),base=base,cp=cp,
        y=np.clip((cp-base)/200.,-2.5,2.5),split=[r['split'] for r in rows],
        kind=[r['kind'] for r in rows],phase=[r['phase'] for r in rows])
    sources=[Path(__file__),selected_path,GM/'preparation.json',GM/'train.json',DESC,SOURCE,
        ROOT/'scripts/continuation_gm_labels.py',ROOT/'docs/CONTINUATION_VALUE_CURRICULUM_PLAN_20260909.md',
        ROOT/'training/residual_value.py',ROOT/'training/rule_value.py',ROOT/'training/daytime_signed_value.py']
    save(OUT/'preparation.json',dict(rows=rows,seed=SEED,candidate=str(candidate.relative_to(ROOT)),
        candidate_files=manifest(candidate),selected_sha256=selected['sha256'],
        sources={str(p):digest(p) for p in sources},dataset_sha256=digest(OUT/'dataset.npz'),
        reserved_full_game_keys=sorted(protected),exclusions=exclusions,conflicts=sorted(conflicts),
        counts=dict(Counter(f'{r["kind"]}-split{r["split"]}' for r in rows)),
        architecture='768x16 clipped ReLU; fixed eight +62.5cp/eight -62.5cp output weights',
        scope='Reused broad development data plus new exposed targets. Three distinct GM game groups reserved; '
              'exact/mirror exclusion against every reserved mainline position. Similar opening families remain in training.'))
    print(json.dumps({'prepared':len(rows),'counts':dict(Counter(r['kind'] for r in rows))}),flush=True)


def fit():
    check_stop()
    prep=json.loads((OUT/'preparation.json').read_text())
    assert all(digest(Path(p))==h for p,h in prep['sources'].items())
    assert not (OUT/'state.json').exists()
    with np.load(OUT/'dataset.npz',allow_pickle=False) as data:
        x,base,cp,y,split,kind,ph=[data[k] for k in ('x','base','cp','y','split','kind','phase')]
    train=np.flatnonzero((split==0)&(kind=='broad'))
    valid=np.flatnonzero(split==1);target=np.flatnonzero(kind!='broad')
    recent=np.flatnonzero(kind=='recent');gm=np.flatnonzero(kind=='gm')
    delta=cp-base
    broad_pools=[train[delta[train]<=-25],train[delta[train]>=25],train[abs(delta[train])<25]]
    target_pools=[target[delta[target]<=-25],target[delta[target]>=25]]
    assert all(len(p)>=16 for p in broad_pools) and all(len(p)>=5 for p in target_pools)
    baseline=float(np.mean(np.minimum((base[valid]-cp[valid])**2,1000000)))
    recent_before=float(np.mean(abs(base[recent]-cp[recent])))
    gm_before=float(np.mean(abs(base[gm]-cp[gm])))
    rng=np.random.default_rng(SEED)
    p=[rng.normal(0,.025,(768,16)).astype(np.float32),np.full(16,.25,dtype=np.float32),
       np.asarray([.3125]*8+[-.3125]*8,dtype=np.float32)]
    m,v=[np.zeros_like(a) for a in p],[np.zeros_like(a) for a in p]
    best,epoch_best,blend_best,steps,retained=baseline,0,0.,0,None
    state=dict(status='training',passed=False,epochs=[],broad_before=baseline,
        recent_before_mae_cp=recent_before,gm_before_mae_cp=gm_before)
    (OUT/'epochs').mkdir()
    for epoch in range(1,25):
        for _ in range((len(train)+255)//256):
            check_stop()
            broad=np.concatenate([rng.choice(pool,size=n,replace=True) for pool,n in zip(broad_pools,(112,112,32))])
            correction=np.concatenate([rng.choice(pool,size=16,replace=True) for pool in target_pools])
            steps+=1
            update_hidden(p,m,v,gradients(x[broad],y[broad],p),gradients(x[correction],y[correction],p),steps)
        raw=np.clip(forward(x,p)[0]*200.,-500,500)
        metrics={}
        for blend in (.25,.5):
            residual=blend*raw
            mse=float(np.mean(np.minimum((base[valid]+residual[valid]-cp[valid])**2,1000000)))
            cohorts=correction_cohorts(base[valid],cp[valid],residual[valid])
            phases={}
            for name,mask in (('endgame',ph[valid]<=8),('other',ph[valid]>8)):
                ids=valid[mask]
                assert len(ids)>=100
                phases[name]=dict(n=len(ids),before=float(np.mean(abs(base[ids]-cp[ids]))),
                    after=float(np.mean(abs(base[ids]+residual[ids]-cp[ids]))))
            recent_after=float(np.mean(abs(base[recent]+residual[recent]-cp[recent])))
            gm_after=float(np.mean(abs(base[gm]+residual[gm]-cp[gm])))
            eligible=(mse<=.99*baseline and cohorts_pass(cohorts)
                and all(r['after']<=r['before'] for r in phases.values())
                and recent_after<=.95*recent_before and gm_after<=gm_before)
            metrics[str(blend)]=dict(capped_mse_cp=mse,cohorts=cohorts,phases=phases,
                recent_mae_cp=recent_after,gm_mae_cp=gm_after,eligible=eligible)
            if eligible and mse<best:
                best,epoch_best,blend_best,retained=mse,epoch,blend,[a.copy() for a in p]
        checkpoint=OUT/'epochs'/f'epoch-{epoch:02d}.npz'
        write_model(checkpoint,p)
        state['epochs'].append(dict(epoch=epoch,metrics=metrics,checkpoint_sha256=digest(checkpoint)))
        save(OUT/'state.json',state)
        print(f'Epoch{epoch}/24 selected{epoch_best} broad{best:.2f}/{baseline:.2f}',flush=True)
    state.update(selected_epoch=epoch_best,value_blend=blend_best,broad_after=best,updates=steps)
    if retained is None:
        state.update(status='complete',decision='reject_before_reserved_labels')
    else:
        write_model(OUT/'value.npz',retained)
        state.update(status='weights_frozen_before_reserved_labels',model_sha256=digest(OUT/'value.npz'),
                     decision='await_reserved_labels')
    assert manifest(ROOT/prep['candidate'])==prep['candidate_files']
    save(OUT/'state.json',state)


def evaluate_reserved():
    check_stop()
    state=json.loads((OUT/'state.json').read_text())
    assert state['status']=='weights_frozen_before_reserved_labels'
    assert digest(OUT/'value.npz')==state['model_sha256']
    labels=json.loads((GM/'reserved_test.json').read_text())
    assert labels['status']=='complete' and labels['frozen_model_sha256']==state['model_sha256']
    prep=json.loads((OUT/'preparation.json').read_text())
    fn=classical(ROOT/prep['candidate'])
    used={r['key'] for r in prep['rows']}
    with np.load(OUT/'value.npz',allow_pickle=False) as data:
        p=[data['weights'],data['bias'],data['output']/200.]
    result=[]
    for r in labels['rows']:
        if not r['eligible']:continue
        assert r['key'] not in used
        board=restore(r)
        base=float(fn(*arrays(board),False))
        residual=state['value_blend']*float(np.clip(forward(features(board)[None,:768],p)[0][0]*200.,-500,500))
        result.append(dict(id=r['id'],group=r['group'],fen=r['fen'],target_stm_cp=r['target_stm_cp'],
            before_cp=base,after_cp=base+residual,before_error_cp=abs(base-r['target_stm_cp']),
            after_error_cp=abs(base+residual-r['target_stm_cp'])))
    before=float(np.mean([r['before_error_cp'] for r in result])) if result else None
    after=float(np.mean([r['after_error_cp'] for r in result])) if result else None
    major_before=sum(r['before_error_cp']>=200 for r in result)
    major_after=sum(r['after_error_cp']>=200 for r in result)
    passed=len(result)>=12 and after<=before and major_after<=major_before
    state.update(status='complete',passed=bool(passed),reserved=result,reserved_eligible=len(result),
        reserved_before_mae_cp=before,reserved_after_mae_cp=after,
        reserved_major_before=major_before,reserved_major_after=major_after,
        decision='eligible_for_runtime_quality_trial' if passed else 'reject_after_reserved_labels',
        finished_utc=datetime.now(timezone.utc).isoformat())
    assert digest(OUT/'value.npz')==state['model_sha256']
    save(OUT/'state.json',state)
    print(json.dumps({k:v for k,v in state.items() if k not in ('epochs','reserved')}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['prepare','fit','evaluate_reserved'],required=True)
    mode=parser.parse_args().mode
    try:
        {'prepare':prepare,'fit':fit,'evaluate_reserved':evaluate_reserved}[mode]()
    except BaseException as error:
        if OUT.exists():
            path=OUT/'state.json'
            state=json.loads(path.read_text()) if path.exists() else {}
            state.update(status='failed',passed=False,error=repr(error))
            save(path,state)
        raise
