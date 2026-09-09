"""One serial bounded architecture test; old fits and reservations preserved."""
import json,os,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
root=Path(__file__).resolve().parent.parent/'outputs/chess-agent';sys.path.insert(0,str(root))
from scripts.continuation_common import RUN,DEADLINE,check_stop,save
from scripts.overnight_capacity import wait_for_capacity
out=RUN/'curriculum-value-supervisor-03';assert not out.exists();out.mkdir(parents=True)
state=dict(status='running',pid=os.getpid(),stages=[])

def stage(name,args,bound):
    check_stop();wait_for_capacity(out/(name+'-capacity.json'),minimum_memory_mb=1400,wait_seconds=0)
    assert (DEADLINE-datetime.now(timezone.utc)).total_seconds()>bound+60
    with (out/(name+'.log')).open('w',encoding='utf-8') as log:
        child=subprocess.Popen([sys.executable,'-X','utf8',*args],cwd=root,stdout=log,stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW)
        row=dict(stage=name,pid=child.pid,status='running');state['stages'].append(row);save(out/'supervisor.json',state)
        started=time.monotonic()
        try:
            while child.poll() is None:
                check_stop()
                if time.monotonic()-started>bound:raise TimeoutError(name)
                time.sleep(2)
            if child.returncode:raise RuntimeError(f'{name} exited{child.returncode}')
        except BaseException:
            if child.poll() is None:
                subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True);child.wait(timeout=10)
            row.update(status='failed',exit_code=child.returncode);raise
        row.update(status='complete',exit_code=child.returncode,seconds=round(time.monotonic()-started,2));save(out/'supervisor.json',state)

try:
    stage('tests',['-m','pytest','-q','tests/test_daytime_antisymmetric.py','tests/test_continuation_perspective_value.py',
        '--junitxml',str(out/'tests.xml')],120)
    prefix=['-m','training.continuation_perspective_value','--mode']
    stage('prepare',prefix+['prepare'],120);stage('fit',prefix+['fit'],300)
    fit=json.loads((RUN/'curriculum-value-03/state.json').read_text())
    if fit['status']=='weights_frozen_before_reserved_labels':
        stage('exposed-colours',prefix+['exposed'],120)
        gate=json.loads((RUN/'curriculum-value-03/exposed-development.json').read_text())
        if gate['passed']:
            stage('label-reserved',prefix+['label_reserved'],240)
            stage('reserved-colours',prefix+['reserved'],120)
    state['status']='complete'
except BaseException as error:
    state.update(status='failed',error=repr(error));raise
finally:
    state['finished_utc']=datetime.now(timezone.utc).isoformat();save(out/'supervisor.json',state)
    print(json.dumps(state),flush=True)
