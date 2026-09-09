"""Serial bounded defensive continuations and independent descendant labels."""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

root=Path(__file__).resolve().parent.parent/'outputs/chess-agent'
sys.path.insert(0,str(root))
from scripts.continuation_common import RUN, DEADLINE, check_stop, save
from scripts.overnight_capacity import wait_for_capacity

out=RUN/'student-descendants-supervisor-01'
assert not out.exists()
out.mkdir(parents=True)
state=dict(status='running',pid=os.getpid(),stages=[])
try:
    check_stop()
    wait_for_capacity(out/'capacity.json',minimum_memory_mb=1400,wait_seconds=0)
    assert (DEADLINE-datetime.now(timezone.utc)).total_seconds()>1300
    for mode,bound,command in [('prepare',30,['-m','scripts.continuation_descendants','--mode','prepare']),('student',480,['-m','scripts.continuation_descendants','--mode','student']),('teacher',600,['-m','scripts.continuation_descendants','--mode','teacher']),('diagnosis',30,['-m','scripts.continuation_value_diagnosis'])]:
        check_stop()
        with (out/(mode+'.log')).open('w',encoding='utf-8') as log:
            child=subprocess.Popen([sys.executable,'-X','utf8',*command],cwd=root,stdout=log,stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW)
            entry=dict(stage=mode,pid=child.pid,status='running')
            state['stages'].append(entry)
            save(out/'supervisor.json',state)
            started=time.monotonic()
            try:
                while child.poll() is None:
                    check_stop()
                    if time.monotonic()-started>bound:raise TimeoutError(mode)
                    time.sleep(2)
                if child.returncode:raise RuntimeError(f'{mode} exited{child.returncode}')
            except BaseException:
                if child.poll() is None:
                    subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
                    child.wait(timeout=10)
                entry.update(status='failed',exit_code=child.returncode)
                raise
            entry.update(status='complete',exit_code=child.returncode,elapsed_seconds=round(time.monotonic()-started,2))
            save(out/'supervisor.json',state)
    state['status']='complete'
except BaseException as error:
    state.update(status='failed',error=repr(error))
    raise
finally:
    state['finished_utc']=datetime.now(timezone.utc).isoformat()
    save(out/'supervisor.json',state)
    print(json.dumps(state),flush=True)
