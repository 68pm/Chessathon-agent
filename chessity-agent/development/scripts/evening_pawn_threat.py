"""Bounded quiet pawn-threat search and independent teacher comparison."""
import argparse
import json
import queue
import shutil
import statistics
import subprocess
import sys
import threading
import xml.etree.ElementTree as ET
from datetime import datetime,timezone
from pathlib import Path
from scripts import daytime_pawn_extrema as trial
from scripts.evening_common import ROOT,RUN,check_stop,digest,manifest,save
from scripts.evening_pawn_threat_transform import transform

OUT=RUN/'pawn-threat-01'
BASE=ROOT/'runs/daytime-20260909/move-buffers-01/prototype'

def prepare():
    from scripts.overnight_archive_challenge import archive_matches
    check_stop()
    assert not OUT.exists()
    speed=RUN/'repetition-02/state.json'
    speed_result=json.loads(speed.read_text())
    assert speed_result['status']=='complete' and speed_result['frozen_candidates']
    parent=RUN/'repetition-02/prototype' if speed_result['passed'] else BASE
    archive_matches(ROOT.parent/'chessity-agent-v1.56.zip',BASE)
    recent=ROOT/'runs/continuation-20260909/student-descendants-01/preparation.json'
    petroff=ROOT/'runs/continuation-20260909/petroff-turning-point-02/preparation.json'
    old=ROOT/'runs/daytime-20260909/exchange-ordering-01/preparation.json'
    roots=[dict(id=r['id'],**{k:r[k] for k in ('start_fen','history','fen')})
           for r in json.loads(recent.read_text())['roots']]
    r=json.loads(petroff.read_text())['root']
    roots.append(dict(id='public-round83-move23',**{k:r[k] for k in ('start_fen','history','fen')}))
    roots+=json.loads(old.read_text())['roots'][:5]
    assert len(roots)==12 and len({r['fen'] for r in roots})==12
    prototype=OUT/'prototype'
    shutil.copytree(parent,prototype,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    source=transform((parent/'engine/compiled_core.py').read_text())
    (prototype/'engine/compiled_core.py').write_text(source,encoding='utf-8',newline='\n')
    experiment=ROOT/'experiments/evening_pawn_threat_core.py'
    assert not experiment.exists()
    experiment.write_text(source,encoding='utf-8',newline='\n')
    paths=[Path(__file__),Path(trial.__file__),ROOT/'scripts/evening_common.py',
        ROOT/'scripts/evening_pawn_threat_transform.py',experiment,speed,recent,petroff,old,
        ROOT/'tests/test_evening_pawn_threat.py',ROOT/'docs/EVENING_PAWN_THREATS_PLAN_20260909.md',
        ROOT/'configs/evening-september9-gate-openings.json',ROOT/'training/game_feedback.py']
    save(OUT/'preparation.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        parent=str(parent.relative_to(ROOT)),
        candidates={'baseline':str(BASE.relative_to(ROOT)),'prototype':str(prototype.relative_to(ROOT))},
        candidate_files={'baseline':manifest(BASE),'prototype':manifest(prototype)},roots=roots,
        source_sha256={str(p.relative_to(ROOT)):digest(p) for p in paths},
        protocol=dict(clock_seconds=1,order=['baseline','prototype','prototype','baseline'],
            teacher_budgets=[80000,320000],deep_root='public-round83-move23',deep_budgets=[2560000,10240000]),
        scope='Quiet pawn-threat LMR protection. Exposed development roots; match openings reserved.'))
    print('Prepared pawn-threat trial, parent='+str(parent.relative_to(ROOT)),flush=True)

class Worker(trial.WarmWorker):
    def __init__(self,label):
        self.label=label
        self.log=(OUT/f'{label}.log').open('w',encoding='utf-8')
        self.answers=queue.Queue()
        self.process=subprocess.Popen([sys.executable,'-X','utf8','-m','scripts.evening_pawn_threat',
            '--worker',label],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,
            text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
        def read():
            for line in self.process.stdout:self.answers.put(line)
            self.answers.put(None)
        threading.Thread(target=read,daemon=True).start()

def controller():
    import chess
    from scripts.overnight_capacity import wait_for_capacity
    from training import game_feedback
    prep=json.loads((OUT/'preparation.json').read_text())
    suite=ET.parse(OUT/'tests.xml').getroot().find('testsuite')
    assert int(suite.attrib['tests'])>=10 and all(int(suite.attrib[k])==0 for k in ('errors','failures','skipped'))
    assert not (OUT/'state.json').exists()
    state=dict(status='running',passed=False,workers={},rows=[],review=[])
    workers={};teacher=None
    save(OUT/'state.json',state)
    try:
        assert all(digest(ROOT/p)==h for p,h in prep['source_sha256'].items())
        for label in ('baseline','prototype'):
            check_stop()
            wait_for_capacity(OUT/f'{label}-capacity.json',minimum_memory_mb=1400,wait_seconds=120)
            workers[label]=Worker(label)
            state['workers'][label]=dict(pid=workers[label].process.pid,status='initializing')
            save(OUT/'state.json',state)
            ready=workers[label].receive(90)
            assert ready['init_seconds']<90
            state['workers'][label].update(ready)
            save(OUT/'state.json',state)
        for index in range(len(prep['roots'])):
            for block,label in enumerate(prep['protocol']['order']):
                check_stop()
                state['rows'].append(workers[label].ask(dict(root=index,regime='clock',block=block)))
                save(OUT/'state.json',state)
        for process in workers.values():process.close()
        workers={}
        check_stop()
        wait_for_capacity(OUT/'teacher-capacity.json',minimum_memory_mb=1400,wait_seconds=120)
        game_feedback.stop_check=check_stop
        teacher=game_feedback.CachedTeacher(ROOT/'data/postgame-feedback/cache-v1',OUT)
        state['status']='reviewing'
        for index,root in enumerate(prep['roots']):
            check_stop()
            board=chess.Board(root['start_fen'])
            for uci in root['history']:board.push_uci(uci)
            assert board.fen()==root['fen']
            budgets=prep['protocol']['deep_budgets'] if root['id']==prep['protocol']['deep_root'] else prep['protocol']['teacher_budgets']
            choices=[r for r in state['rows'] if r['root']==index]
            bests=[teacher.analyse(board,n) for n in budgets]
            values={uci:[best if best['pv'][0]==uci else teacher.analyse(board,n,chess.Move.from_uci(uci))
                         for n,best in zip(budgets,bests,strict=True)] for uci in sorted({r['uci'] for r in choices})}
            reviewed=[]
            for choice in choices:
                selected=values[choice['uci']]
                regrets=[max(0,a['cp']-b['cp']) if a['cp'] is not None and b['cp'] is not None else None
                         for a,b in zip(bests,selected,strict=True)]
                reviewed.append(dict(**choice,values=selected,regret_cp=regrets,
                    major=all(v is not None and v>=200 for v in regrets),
                    mate_loss=any(v['mate'] is not None and v['mate']<0 for v in selected)))
            state['review'].append(dict(id=root['id'],budgets=budgets,best=bests,choices=reviewed))
            save(OUT/'state.json',state)
            print(f'Reviewed {index+1}/12 roots',flush=True)
        finite=[r for r in state['review'] if all(v is not None for c in r['choices'] for v in c['regret_cp'])]
        assert finite
        means={label:[statistics.mean(c['regret_cp'][i] for r in finite for c in r['choices'] if c['label']==label)
                      for i in range(2)] for label in ('baseline','prototype')}
        regressions={field:[r['id'] for r in state['review'] if
            sum(c[field] for c in r['choices'] if c['label']=='prototype')>
            sum(c[field] for c in r['choices'] if c['label']=='baseline')]
            for field in ('major','mate_loss')}
        passed=(not any(regressions.values()) and
            all(a<=b for a,b in zip(means['prototype'],means['baseline'],strict=True)) and
            any(b>0 and a<=.9*b for a,b in zip(means['prototype'],means['baseline'],strict=True)))
        state.update(status='complete',passed=passed,mean_regret_cp=means,finite_roots=len(finite),
            regressions=regressions,decision='needs_read_only_and_short_matches' if passed else 'reject_quality_gate')
    except BaseException as error:
        state.update(status='failed',passed=False,error=repr(error));raise
    finally:
        for process in workers.values():process.close()
        if teacher:
            teacher.close();state['requested_teacher_nodes']=teacher.requested_nodes
        state['frozen_candidates']=all(manifest(ROOT/p)==prep['candidate_files'][label] for label,p in prep['candidates'].items())
        if not state['frozen_candidates']:state.update(status='failed',passed=False,error='Candidate mutated')
        state['finished_utc']=datetime.now(timezone.utc).isoformat()
        save(OUT/'state.json',state)
        print(json.dumps({k:v for k,v in state.items() if k not in ('rows','review')}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--worker',choices=('baseline','prototype'))
    args=parser.parse_args()
    if args.prepare:prepare()
    elif args.worker:
        trial.OUT,trial.check_stop=OUT,check_stop
        trial.worker(args.worker)
    else:controller()
