"""Isolated sixteen-unit integration and short equal-clock search diagnostics."""
import argparse
import json
import queue
import shutil
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

from scripts.continuation_common import ROOT,RUN,check_stop,digest,manifest,save
from scripts.daytime_pawn_extrema import WarmWorker

OUT=RUN/'curriculum-value-runtime-01'
FIT=RUN/'curriculum-value-02'


def prepare():
    check_stop();assert not OUT.exists()
    fit=json.loads((FIT/'state.json').read_text())
    assert fit['status']=='complete' and fit['passed'] and fit['decision']=='eligible_for_runtime_quality_trial'
    assert digest(FIT/'value.npz')==fit['model_sha256']
    selected=json.loads((ROOT.parent/'chessity-agent-version.json').read_text())
    assert selected['version']=='v1.56' and digest(ROOT.parent/'chessity-agent.zip')==selected['sha256']
    baseline=ROOT/selected['source_version'];prototype=OUT/'prototype'
    shutil.copytree(baseline,prototype,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    driver=prototype/'engine/compiled_driver.py';source=driver.read_text()
    old="assert self.weights.shape == (768, 32) and self.bias.shape == self.output.shape == (32,)"
    new="assert self.weights.shape == (768, 16) and self.bias.shape == self.output.shape == (16,)"
    assert source.count(old)==1
    source=source.replace(old,new);driver.write_text(source,encoding='utf-8',newline='\n')
    experimental=ROOT/'experiments/continuation_colour_value_driver.py';assert not experimental.exists()
    experimental.write_text(source,encoding='utf-8',newline='\n')
    shutil.copyfile(FIT/'value.npz',prototype/'models/value.npz')
    config_path=prototype/'runtime.json';config=json.loads(config_path.read_text())
    config.update(residual_value=True,value_blend=fit['value_blend']);save(config_path,config)
    before,after=manifest(baseline),manifest(prototype)
    changed={p for p in before.keys()|after.keys() if before.get(p)!=after.get(p)}
    assert changed=={'engine/compiled_driver.py','models/value.npz','runtime.json'}
    recent=json.loads((RUN/'student-descendants-01/preparation.json').read_text())['roots']
    old_roots=json.loads((ROOT/'runs/daytime-20260909/move-buffers-01/preparation.json').read_text())['roots'][:6]
    roots=[{k:r[k] for k in ('id','start_fen','history','fen')} for r in recent+old_roots]
    assert len(roots)==len({r['fen'] for r in roots})==12
    paths=[Path(__file__),experimental,FIT/'state.json',FIT/'preparation.json',FIT/'value.npz',
        FIT/'exposed-development.json',FIT/'reserved-evaluation.json',
        ROOT/'docs/CONTINUATION_VALUE_RUNTIME_PLAN_20260909.md',ROOT/'scripts/daytime_pawn_extrema.py']
    save(OUT/'preparation.json',dict(candidates={'baseline':str(baseline.relative_to(ROOT)),
        'prototype':str(prototype.relative_to(ROOT))},candidate_files={'baseline':before,'prototype':after},
        roots=roots,sources={str(p):digest(p) for p in paths},model_sha256=fit['model_sha256'],
        protocol=dict(seconds=[1,3],order=['baseline','prototype','prototype','baseline']),
        scope='Exposed targeted equal-clock development check. No independent rating claim.'))
    print('Prepared isolated sixteen-unit runtime candidate',flush=True)


def numerical(agent,driver):
    import chess
    import numpy as np
    core=driver.core;search=agent._search
    assert search.weights.shape==(768,16)
    rng=np.random.default_rng(2026090918)
    positions=[chess.Board(f) for f in (
        chess.STARTING_FEN,'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1',
        '4k3/P7/8/8/8/8/7p/4K3 w - - 0 1',
        '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2')]
    for _ in range(4):
        board=chess.Board()
        for ply in range(40):
            if board.is_game_over():break
            board.push(list(board.legal_moves)[int(rng.integers(board.legal_moves.count()))])
            if ply%4==0:positions.append(board.copy(stack=True))
    positions += [b.mirror() for b in list(positions)]
    checked=0;maximum=0.
    for board in positions:
        pieces,state=driver.arrays(board);acc=core.build_accumulator(pieces,search.weights,search.bias)
        for c,side in ((0,True),(1,False)):
            x=np.zeros(768,dtype=np.float64)
            for square,piece in board.piece_map().items():
                channel=piece.piece_type-1+(0 if piece.color==side else 6)
                relative=square if side else chess.square_mirror(square)
                x[64*channel+relative]=1
            dense=x@search.weights.astype(np.float64)+search.bias.astype(np.float64)
            assert np.max(abs(acc[c]-dense))<=1e-9
        base=core.classical(pieces,state,search.conversion)
        dense_residual=float(np.clip(acc[0 if board.turn else 1],0,1)@search.output)
        expected=base+round(search.blend*min(500,max(-500,dense_residual)))
        actual=core.evaluate_accumulator(pieces,state,search.output,search.blend,search.conversion,acc)
        assert abs(actual-expected)<=1
        original=pieces.copy(),state.copy(),acc.copy()
        encoded=list(core.legal_moves(pieces,state))
        assert {driver.decode(int(m)) for m in encoded}==set(board.legal_moves)
        for move in encoded:
            old=core.make(pieces,state,move);core.update_accumulator(acc,search.weights,move,old,1)
            py=board.copy(stack=True);py.push(driver.decode(int(move)))
            pb,ps=driver.arrays(py)
            assert np.array_equal(pieces,pb) and np.array_equal(state,ps)
            rebuilt=core.build_accumulator(pieces,search.weights,search.bias)
            difference=float(np.max(abs(acc-rebuilt)));maximum=max(maximum,difference)
            assert difference<=1e-9
            core.update_accumulator(acc,search.weights,move,old,-1);core.unmake(pieces,state,move,old)
            assert np.array_equal(pieces,original[0]) and np.array_equal(state,original[1])
            assert np.max(abs(acc-original[2]))<=1e-9
            checked+=1
    assert checked>=500
    return dict(positions=len(positions),legal_make_unmake_checks=checked,maximum_accumulator_difference=maximum)


def worker(label):
    prep=json.loads((OUT/'preparation.json').read_text());candidate=ROOT/prep['candidates'][label]
    sys.path.insert(0,str(candidate));tick=time.perf_counter()
    import chess
    import agent
    driver=sys.modules['engine.compiled_driver'];core=driver.core
    assert Path(core.__file__).resolve()==candidate/'engine/compiled_core.py'
    checks=numerical(agent,driver) if label=='prototype' else None
    print(json.dumps(dict(status='ready',init_seconds=time.perf_counter()-tick,numerical=checks)),flush=True)
    signatures=tuple(map(str,core.search.signatures))
    for line in sys.stdin:
        request=json.loads(line)
        if request.get('stop'):return
        check_stop();row=prep['roots'][request['root']]
        board=chess.Board(row['start_fen'])
        for uci in row['history']:board.push_uci(uci)
        assert board.fen()==row['fen'];history=board.move_stack.copy()
        for key in ('ttkey','ttcontext','ttdata','killers','history'):getattr(agent._search,key).fill(0)
        seconds=request['seconds'];started=time.process_time()
        preferred=agent.alien_move(board) if agent._config.get('opening_style')=='alien-selective' else None
        result=agent._search.run(board,seconds,seconds,preferred_move=preferred,preference_cp=agent._config.get('alien_cp',15))
        cpu=time.process_time()-started
        assert result.move in board.legal_moves and board.fen()==row['fen'] and board.move_stack==history
        assert tuple(map(str,core.search.signatures))==signatures and result.elapsed<=seconds+.3
        print(json.dumps(dict(**request,id=row['id'],label=label,uci=result.move.uci(),score=result.score,
            depth=result.depth,nodes=result.nodes,elapsed=result.elapsed,cpu_seconds=cpu)),flush=True)


class Worker(WarmWorker):
    def __init__(self,label):
        self.label=label;self.log=(OUT/(label+'.log')).open('w',encoding='utf-8');self.answers=queue.Queue()
        self.process=subprocess.Popen([sys.executable,'-X','utf8','-m','scripts.continuation_value_runtime','--worker',label],
            cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,text=True,encoding='utf-8',
            creationflags=subprocess.CREATE_NO_WINDOW)
        def read():
            for line in self.process.stdout:self.answers.put(line)
            self.answers.put(None)
        threading.Thread(target=read,daemon=True).start()


def measure():
    from scripts.overnight_capacity import wait_for_capacity
    prep=json.loads((OUT/'preparation.json').read_text());assert not (OUT/'measurement.json').exists()
    assert all(digest(Path(p))==h for p,h in prep['sources'].items())
    workers={};state=dict(status='running',workers={},rows=[])
    try:
        for label in ('baseline','prototype'):
            check_stop();wait_for_capacity(OUT/(label+'-capacity.json'),minimum_memory_mb=1400,wait_seconds=0)
            workers[label]=Worker(label);ready=workers[label].receive(90)
            assert ready['status']=='ready' and ready['init_seconds']<90
            state['workers'][label]=dict(pid=workers[label].process.pid,**ready);save(OUT/'measurement.json',state)
        for index in range(len(prep['roots'])):
            for seconds in (1,3):
                for block,label in enumerate(('baseline','prototype','prototype','baseline')):
                    check_stop();state['rows'].append(workers[label].ask(dict(root=index,seconds=seconds,block=block)))
                    save(OUT/'measurement.json',state)
        assert len(state['rows'])==96
        state['status']='complete'
    except BaseException as error:
        state.update(status='failed',error=repr(error));raise
    finally:
        for value in workers.values():value.close()
        state['frozen_candidates']=all(manifest(ROOT/p)==prep['candidate_files'][label] for label,p in prep['candidates'].items())
        assert state['frozen_candidates'];save(OUT/'measurement.json',state)


def review():
    import chess
    from training import game_feedback
    from scripts.overnight_capacity import wait_for_capacity
    check_stop();prep=json.loads((OUT/'preparation.json').read_text())
    measured=json.loads((OUT/'measurement.json').read_text());assert measured['status']=='complete'
    assert not (OUT/'quality.json').exists()
    wait_for_capacity(OUT/'review-capacity.json',minimum_memory_mb=1400,wait_seconds=0)
    game_feedback.stop_check=check_stop;teacher=game_feedback.CachedTeacher(ROOT/'data/postgame-feedback/cache-v1',OUT)
    state=dict(status='running',passed=False,review=[])
    try:
        for i,root in enumerate(prep['roots']):
            check_stop();board=chess.Board(root['start_fen'])
            for uci in root['history']:board.push_uci(uci)
            assert board.fen()==root['fen']
            choices=[r for r in measured['rows'] if r['root']==i];assert len(choices)==8
            best=[teacher.analyse(board,n) for n in (80000,320000)]
            values={uci:[b if b['pv'][0]==uci else teacher.analyse(board,n,chess.Move.from_uci(uci))
                for n,b in zip((80000,320000),best,strict=True)] for uci in sorted({c['uci'] for c in choices})}
            reviewed=[]
            for c in choices:
                selected=values[c['uci']]
                regrets=[max(0,b['cp']-v['cp']) if b['cp'] is not None and v['cp'] is not None else None for b,v in zip(best,selected,strict=True)]
                reviewed.append(dict(**c,values=selected,regret_cp=regrets,
                    major=all(v is not None and v>=200 for v in regrets),
                    mate_loss=any(v['mate'] is not None and v['mate']<0 for v in selected)))
            state['review'].append(dict(id=root['id'],best=best,choices=reviewed));save(OUT/'quality.json',state)
        means={};regressions=[]
        for seconds in (1,3):
            finite=[r for r in state['review'] if all(v is not None for c in r['choices'] if c['seconds']==seconds for v in c['regret_cp'])]
            assert len(finite)>=6
            means[str(seconds)]={label:[statistics.mean(c['regret_cp'][k] for r in finite for c in r['choices']
                if c['seconds']==seconds and c['label']==label) for k in range(2)] for label in ('baseline','prototype')}
            for row in state['review']:
                for field in ('major','mate_loss'):
                    counts={label:sum(c[field] for c in row['choices'] if c['label']==label and c['seconds']==seconds) for label in ('baseline','prototype')}
                    if counts['prototype']>counts['baseline']:regressions.append(dict(id=row['id'],seconds=seconds,kind=field))
        passed=(not regressions and all(a<=b for a,b in zip(means['1']['prototype'],means['1']['baseline']))
            and all(a<b for a,b in zip(means['3']['prototype'],means['3']['baseline'])))
        state.update(status='complete',passed=bool(passed),mean_regret_cp=means,regressions=regressions,
            decision='eligible_short_match_screen' if passed else 'reject_runtime_quality')
    except BaseException as error:
        state.update(status='failed',error=repr(error));raise
    finally:
        teacher.close();state['requested_teacher_nodes']=teacher.requested_nodes
        state['frozen_candidates']=all(manifest(ROOT/p)==prep['candidate_files'][label] for label,p in prep['candidates'].items())
        assert state['frozen_candidates'];save(OUT/'quality.json',state)
    print(json.dumps({k:v for k,v in state.items() if k!='review'}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['prepare','measure','review']);parser.add_argument('--worker',choices=['baseline','prototype'])
    args=parser.parse_args()
    worker(args.worker) if args.worker else {'prepare':prepare,'measure':measure,'review':review}[args.mode]()
