"""Resume a declared sequence of experiments, then return to evidence-based critique."""

import argparse
import ctypes
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.alien_rating_ladder import save_json, sha256
from training.fastchess_data import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    out = ROOT / plan['output']
    out.mkdir(parents=True, exist_ok=True)
    status_file = out / 'controller.json'
    previous = json.loads(status_file.read_text()) if status_file.exists() else {}
    if previous:
        assert previous['plan_sha256'] == sha256(args.plan)
    if previous.get('status') == 'complete':
        return
    state = dict(plan_sha256=sha256(args.plan), pid=os.getpid(), status='waiting',
                 stage='prerequisites', started_utc=datetime.now(timezone.utc).isoformat(),
                 completed_stages=previous.get('completed_stages', []))
    lock = out / 'controller.lock'
    # A durable lock plus recorded PID prevents duplicate controllers. Stale locks
    # require checking the real process before removal; never blindly break one.
    handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(handle, str(os.getpid()).encode())
    os.close(handle)
    save_json(status_file, state)
    if os.name == 'nt':
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        while True:
            if (ROOT / 'STOP_TRAINING').exists() or (ROOT / 'STOP_BENCHMARK').exists():
                raise InterruptedError('User stop flag')
            ready = True
            for prerequisite in plan.get('wait_for', []):
                path = ROOT / prerequisite
                if not path.exists():
                    ready = False
                    continue
                report = json.loads(path.read_text())
                if report.get('status') == 'failed':
                    raise RuntimeError(f'Prerequisite failed: {prerequisite}')
                ready &= report.get('status') == 'complete'
            if ready:
                break
            time.sleep(15)
        for stage in plan['stages']:
            if stage['name'] in state['completed_stages']:
                continue
            if (ROOT / 'STOP_TRAINING').exists() or (ROOT / 'STOP_BENCHMARK').exists():
                raise InterruptedError('User stop flag')
            state.update(status='running', stage=stage['name'])
            save_json(status_file, state)
            with (out / (stage['name'] + '.log')).open('a', encoding='utf-8') as log:
                subprocess.run([sys.executable, '-m', stage['module'], *stage['arguments']],
                               cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True,
                               creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            state['completed_stages'].append(stage['name'])
            save_json(status_file, state)
        state.update(status='complete', stage='awaiting_critique', completed_utc=datetime.now(timezone.utc).isoformat())
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(status_file, state)
        lock.unlink()
        if os.name == 'nt':
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == '__main__':
    main()
