"""Serial student and independent teacher diagnosis after the completed short screen."""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

root = Path(__file__).resolve().parent.parent / 'outputs/chess-agent'
sys.path.insert(0, str(root))
from scripts.daytime_common import DEADLINE, check_stop, save
from scripts.overnight_capacity import wait_for_capacity

out = root / 'runs/daytime-20260909/student-descendants-supervisor-03'
previous=json.loads((root/'runs/daytime-20260909/move-buffers-screen-supervisor-01/supervisor.json').read_text())
assert previous['status']=='complete' and all(r['status']=='complete' for r in previous['stages'])
assert (DEADLINE - datetime.now(timezone.utc)).total_seconds() > 1200
status = out / 'supervisor.json'
assert not status.exists(), 'Preserve consumed trials.'
record = dict(status='running', pid=os.getpid(), stages=[])
save(status, record)
try:
    check_stop()
    wait_for_capacity(out / 'capacity.json', minimum_memory_mb=1400, wait_seconds=120)
    command = [sys.executable, '-X', 'utf8', '-m', 'scripts.daytime_buffer_descendants']
    stages = [(label, [*command, '--mode', label], bound)
        for label, bound in [('prepare', 60), ('student', 480), ('teacher', 600)]]
    stages.append(('diagnosis', [sys.executable, '-X', 'utf8', '-m',
        'scripts.daytime_buffer_value_diagnosis'], 30))
    for label, arguments, bound in stages:
        check_stop()
        assert (DEADLINE - datetime.now(timezone.utc)).total_seconds() > bound + 120
        with (out / f'{label}.log').open('w', encoding='utf-8') as log:
            process = subprocess.Popen(arguments, cwd=root, stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            entry = dict(label=label, pid=process.pid, status='running', timeout_seconds=bound)
            record['stages'].append(entry)
            save(status, record)
            started = time.monotonic()
            try:
                while process.poll() is None:
                    check_stop()
                    if time.monotonic() - started >= bound:
                        raise TimeoutError(f'{label} exceeded {bound}s')
                    time.sleep(2)
                code = process.returncode
            except BaseException as error:
                entry.update(status='failed', error=repr(error))
                if process.poll() is None:
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                    process.wait(timeout=10)
                raise
        entry.update(status='complete' if code == 0 else 'failed', exit_code=code,
            elapsed_seconds=round(time.monotonic() - started, 2))
        save(status, record)
        if code:
            raise RuntimeError(f'{label} exited {code}; inspect preserved log')
        print(f'{label} complete', flush=True)
    record['status'] = 'complete'
except BaseException as error:
    record.update(status='failed', error=repr(error))
    raise
finally:
    record['finished_utc'] = datetime.now(timezone.utc).isoformat()
    save(status, record)
    print(json.dumps(record), flush=True)
