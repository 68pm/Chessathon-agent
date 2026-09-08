"""Strict read-only validation with separate startup and post-ready watchdogs."""
import argparse
import hashlib
import json
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
import zipfile
from pathlib import Path

from scripts.alien_rating_ladder import save_json
from scripts.validate_package import PROBE


def run_probe(program, cwd, arguments, out, startup_seconds=90, ready_seconds=30):
    """Own only this child tree; persist stage measurements even on failure."""
    messages = queue.Queue()
    errors = []
    state = dict(status='running', stage='startup', startup_limit_seconds=startup_seconds,
                 post_ready_limit_seconds=ready_seconds, events=[])
    started = time.monotonic()
    deadline = started + startup_seconds
    answer = None
    with subprocess.Popen([sys.executable, '-B', '-c', program, *map(str, arguments)], cwd=cwd,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0) as process:
        def read_stdout():
            for line in process.stdout:
                messages.put(line)
            messages.put(None)

        def read_stderr():
            errors.extend(process.stderr)

        readers = [threading.Thread(target=read_stdout, daemon=True), threading.Thread(target=read_stderr, daemon=True)]
        for reader in readers:
            reader.start()
        try:
            while True:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError(f"{state['stage']} deadline exceeded")
                try:
                    line = messages.get(timeout=min(.2, remaining))
                except queue.Empty:
                    continue
                if line is None:
                    break
                item = json.loads(line)
                state['events'].append(item)
                if item.get('event') == 'ready':
                    assert state['stage'] == 'startup' and item['init_ms'] < startup_seconds * 1000
                    state.update(stage='move-and-feature-checks', init_ms=item['init_ms'])
                    deadline = time.monotonic() + ready_seconds
                else:
                    assert state['stage'] == 'move-and-feature-checks'
                    answer = item
                save_json(out.with_suffix('.progress.json'), state)
            code = process.wait(timeout=max(.01, deadline - time.monotonic()))
            assert code == 0 and answer is not None, f'Probe exit{code}: {"".join(errors)[-2000:]}'
            state['status'] = 'complete'
            return answer, state
        except BaseException as error:
            state.update(status='failed', error=repr(error))
            if process.poll() is None:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                        capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    process.kill()
            process.wait(timeout=15)
            raise
        finally:
            for reader in readers:
                reader.join(timeout=2)
            state['elapsed_seconds'] = time.monotonic() - started
            state['stderr'] = ''.join(errors)
            save_json(out.with_suffix('.progress.json'), state)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--zip', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--clock-ms', type=int, default=120000)
    parser.add_argument('--calls', type=int, default=2)
    args = parser.parse_args()
    assert not args.out.exists() and not args.out.with_suffix('.progress.json').exists()
    assert args.calls == 2 and args.clock_ms == 120000
    needle = 'init_ms = (time.perf_counter() - start) * 1000\n'
    assert PROBE.count(needle) == 1
    program = PROBE.replace(needle, needle + "print(json.dumps({'event':'ready','init_ms':init_ms}),flush=True)\n")
    with tempfile.TemporaryDirectory(prefix='chessity-staged-check-') as temporary:
        with zipfile.ZipFile(args.zip) as package:
            names = package.namelist()
            assert 'agent.py' in names
            assert sum(i.file_size for i in package.infolist()) < 50_000_000
            for name in names:
                assert not Path(name).is_absolute() and '..' not in Path(name).parts
            package.extractall(temporary)
        result, stages = run_probe(program, temporary, [args.clock_ms,args.calls], args.out)
    assert result['init_ms'] < 90000 and result['legal_calls'] == 2
    assert result['policy_calls'] == 2 and result['max_move_ms'] < 120000
    if result['peak_working_set_bytes'] is not None:
        assert result['peak_working_set_bytes'] < 2_000_000_000
    result.update(status='complete', sha256=hashlib.sha256(args.zip.read_bytes()).hexdigest(),
                  size_bytes=args.zip.stat().st_size, stages=stages)
    save_json(args.out,result)


if __name__ == '__main__':
    main()
