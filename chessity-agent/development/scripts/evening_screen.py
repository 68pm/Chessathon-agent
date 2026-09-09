"""Short challenger gate: exact selected release first, rated settings second."""
import argparse
import json
import subprocess
import sys
import time
import zipfile
from datetime import datetime,timezone
from pathlib import Path
from scripts.evening_common import ROOT,RUN,DEADLINE,check_stop,digest,manifest,save
from scripts.daytime_move_buffers_screen import operationally_clean,pair_passes,qualifies_2800
from scripts.overnight_archive_challenge import archive_matches
from scripts.overnight_portable_fast_screen import audit_feedback

BASE=ROOT/'runs/daytime-20260909/move-buffers-01/prototype'
SOURCE=RUN/'pawn-threat-01'
OUT=RUN/'pawn-threat-screen-01'
OPENINGS='configs/evening-september9-gate-openings.json'
CYCLE_PREFIX='e9-pawn-threat-01-'

def challenger_passes(pairs):
    return len(pairs)==2 and all(pair_passes(p,0) for p in pairs) and sum(g['score'] for p in pairs for g in p)>=3

def all_required_pass(played):
    return (challenger_passes([played.get('versus56-b12',[]),played.get('versus56-d48',[])])
        and pair_passes(played.get('rated2400',[]),1)
        and pair_passes(played.get('rated2600',[]),.5)
        and all(operationally_clean(games) for games in played.values()))

def prepare():
    check_stop()
    assert not OUT.exists()
    state=json.loads((SOURCE/'state.json').read_text())
    assert state['status']=='complete' and state['passed'] and state['frozen_candidates']
    original=json.loads((SOURCE/'preparation.json').read_text())
    candidate=ROOT/original['candidates']['prototype']
    assert all(manifest(ROOT/p)==original['candidate_files'][label] for label,p in original['candidates'].items())
    selected=json.loads((ROOT.parent/'chessity-agent-version.json').read_text())
    assert selected['version']=='v1.56' and digest(ROOT.parent/'chessity-agent.zip')==selected['sha256']
    archive_matches(ROOT.parent/'chessity-agent.zip',BASE)
    OUT.mkdir()
    package=OUT/'challenger.zip'
    with zipfile.ZipFile(package,'x',zipfile.ZIP_DEFLATED) as z:
        for name in manifest(candidate):z.write(candidate/name,name)
    archive_matches(package,candidate)
    paths=[Path(__file__),ROOT/'scripts/evening_common.py',ROOT/'tests/test_evening_screen.py',
        ROOT/OPENINGS,ROOT/'configs/overnight-opponent-pool.json',
        ROOT/'scripts/feedback_matches.py',ROOT/'scripts/feedback_matches_windows.py',
        ROOT/'scripts/overnight_matches.py',ROOT/'scripts/overnight_game.py',
        ROOT/'scripts/overnight_portable_fast_screen.py',ROOT/'scripts/daytime_move_buffers_screen.py',
        ROOT/'scripts/validate_package_staged_fixed.py',ROOT/'scripts/validate_package.py',
        ROOT/'training/game_feedback.py',ROOT/'training/reward_policy.py',
        SOURCE/'state.json',SOURCE/'preparation.json']
    save(OUT/'preparation.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        candidate=str(candidate.relative_to(ROOT)),files={str(p.relative_to(ROOT)):manifest(p) for p in (candidate,BASE)},
        selected_sha256=selected['sha256'],package_sha256=digest(package),
        source_sha256={str(p.relative_to(ROOT)):digest(p) for p in paths},
        matches=[dict(label='versus56-b12',opponent=str(BASE.relative_to(ROOT)),offset=0),
                 dict(label='versus56-d48',opponent=str(BASE.relative_to(ROOT)),offset=1),
                 dict(label='rated2400',level=2400,offset=2),dict(label='rated2600',level=2600,offset=2)],
        qualification='>=3/4 exactv1.56; >=1/2 nominal2400; >=0.5/2 nominal2600; all reviewed and operationally clean.',
        scope='Small practical screen; no calibrated Elo or universal strength proof. No automatic selection in runner.'))
    print('Prepared strictly gated challenger screen',flush=True)

def run():
    from scripts.overnight_capacity import wait_for_capacity
    prep=json.loads((OUT/'preparation.json').read_text())
    assert not (OUT/'state.json').exists()
    package=OUT/'challenger.zip'
    state=dict(status='running',passed=False,stages=[],matches=[])
    save(OUT/'state.json',state)
    def verify():
        assert all(manifest(ROOT/p)==h for p,h in prep['files'].items())
        assert all(digest(ROOT/p)==h for p,h in prep['source_sha256'].items())
        assert digest(package)==prep['package_sha256']
        assert digest(ROOT.parent/'chessity-agent.zip')==prep['selected_sha256']
    def stage(label,arguments,budget):
        check_stop();verify()
        assert (DEADLINE-datetime.now(timezone.utc)).total_seconds()>budget+120,'Stage cannot finish within declared bound'
        wait_for_capacity(OUT/f'{label}-capacity.json',minimum_memory_mb=1400,wait_seconds=120)
        row=dict(label=label,status='running',arguments=arguments,timeout_seconds=budget)
        state['stages'].append(row)
        tick=time.monotonic()
        with (OUT/f'{label}.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen([sys.executable,'-X','utf8','-m',*arguments],cwd=ROOT,
                stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
            row['pid']=process.pid;save(OUT/'state.json',state)
            try:
                while process.poll() is None:
                    check_stop()
                    if time.monotonic()-tick>budget:raise TimeoutError(f'{label} exceeded declared bound')
                    time.sleep(.5)
                assert process.returncode==0,f'{label} exited{process.returncode}; inspect log'
                row['status']='complete'
            except BaseException as error:
                row.update(status='failed',error=repr(error))
                if process.poll() is None:
                    subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],capture_output=True,check=True,creationflags=subprocess.CREATE_NO_WINDOW)
                    process.wait(timeout=15)
                raise
            finally:
                row['elapsed_seconds']=time.monotonic()-tick;save(OUT/'state.json',state)
        verify()
    def match(row):
        kind='rated' if 'level' in row else 'comparison'
        cycle=CYCLE_PREFIX+row['label']
        arguments=['scripts.feedback_matches_windows','--candidate',prep['candidate'],'--stage',kind,
            '--pairs','1','--offset',str(row['offset']),'--cycle',cycle,'--openings',OPENINGS]
        arguments+=['--levels',str(row['level'])] if 'level' in row else ['--opponent',row['opponent']]
        stage(row['label'],arguments,1500)
        path=ROOT/'runs/improvement-loop-20260907'/cycle/f'{kind}-{Path(prep["candidate"]).name}/results.json'
        result=audit_feedback(path)
        state['matches'].append(dict(**row,result_path=str(path.relative_to(ROOT)),sha256=digest(path),summary=result['summary']))
        save(OUT/'state.json',state)
        return result['games']
    played={}
    try:
        stage('read-only',['scripts.validate_package_staged_fixed','--zip',str(package),'--out',str(OUT/'validation.json')],180)
        validation=json.loads((OUT/'validation.json').read_text())
        assert validation['status']=='complete' and validation['sha256']==prep['package_sha256']
        for row in prep['matches']:
            games=played[row['label']]=match(row)
            if not pair_passes(games,0):
                state.update(status='complete',decision='reject_operational_or_incomplete_pair');return
            score=sum(g['score'] for g in games)
            if row['label']=='versus56-b12' and score<1:
                state.update(status='complete',decision='reject_challenger_gate_already_impossible');return
            if row['label']=='versus56-d48' and not challenger_passes([played['versus56-b12'],games]):
                state.update(status='complete',decision='reject_challenger_gate');return
            if row['label']=='rated2400' and score<1:
                state.update(status='complete',decision='reject_2400_gate');return
            if row['label']=='rated2600' and score<.5:
                state.update(status='complete',decision='reject_2600_gate');return
        if qualifies_2800(played['rated2600']):
            played['rated2800']=match(dict(label='rated2800',level=2800,offset=2))
        state.update(status='complete',passed=all_required_pass(played),
            decision='qualified_for_release_review' if all_required_pass(played) else 'retain_v156')
    except BaseException as error:
        state.update(status='failed',passed=False,error=repr(error));raise
    finally:
        state['frozen_candidates']=all(manifest(ROOT/p)==h for p,h in prep['files'].items())
        if not state['frozen_candidates']:state.update(status='failed',passed=False,error='Candidate mutated')
        state['finished_utc']=datetime.now(timezone.utc).isoformat()
        save(OUT/'state.json',state)
        print(json.dumps({k:v for k,v in state.items() if k!='stages'}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true')
    args=parser.parse_args()
    prepare() if args.prepare else run()
