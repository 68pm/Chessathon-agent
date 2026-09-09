"""Two reviewed current-release games for diagnosis, never promotion evidence."""
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from scripts.progression_common import ROOT, RUN, BASE, DEADLINE, check_stop, digest, manifest, save
from scripts.overnight_archive_challenge import archive_matches
from scripts.overnight_portable_fast_screen import audit_feedback
from scripts.overnight_capacity import wait_for_capacity

OUT = RUN / 'v156-development2400-01'
CYCLE = 'p9-v156-development2400-01'


def run():
    check_stop()
    assert not OUT.exists()
    assert (DEADLINE - datetime.now(timezone.utc)).total_seconds() > 1620
    archive_matches(ROOT.parent / 'chessity-agent-v1.56.zip', BASE)
    files = manifest(BASE)
    OUT.mkdir(parents=True)
    result_path = ROOT / 'runs/improvement-loop-20260907' / CYCLE / 'rated-prototype/results.json'
    assert not result_path.parent.exists()
    arguments = ['scripts.feedback_matches_windows', '--candidate', str(BASE.relative_to(ROOT)),
        '--stage', 'rated', '--pairs', '1', '--offset', '0', '--cycle', CYCLE,
        '--openings', 'configs/evening-september9-gate-openings.json', '--levels', '2400']
    sources = [Path(__file__), ROOT / 'scripts/progression_common.py',
        ROOT / 'scripts/feedback_matches_windows.py', ROOT / 'scripts/feedback_matches.py',
        ROOT / 'training/game_feedback.py', ROOT / 'training/reward_policy.py',
        ROOT / 'configs/evening-september9-gate-openings.json']
    prep = dict(candidate=str(BASE.relative_to(ROOT)), files=files,
        selected_sha256=digest(ROOT.parent / 'chessity-agent-v1.56.zip'),
        sources={str(p.relative_to(ROOT)): digest(p) for p in sources}, arguments=arguments,
        scope='Two v1.56 development games against nominal2400 on already exposed B12. '
              'Not successor qualification, calibrated Elo or the reserved three-pair confirmation.')
    save(OUT / 'preparation.json', prep)
    wait_for_capacity(OUT / 'capacity.json', minimum_memory_mb=1400, wait_seconds=120)
    state = dict(status='running', passed=False)
    tick = time.monotonic()
    with (OUT / 'match.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, '-X', 'utf8', '-m', *arguments], cwd=ROOT,
            stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        state['pid'] = process.pid; save(OUT / 'state.json', state)
        try:
            while process.poll() is None:
                check_stop()
                if time.monotonic() - tick > 1500:
                    raise TimeoutError('Development pair exceeded25-minute watchdog')
                time.sleep(.5)
            assert process.returncode == 0
            result = audit_feedback(result_path)
            state.update(status='complete', result_path=str(result_path.relative_to(ROOT)),
                         result_sha256=digest(result_path), summary=result['summary'])
        except BaseException as error:
            state.update(status='failed', error=repr(error))
            if process.poll() is None:
                subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                    capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                process.wait(timeout=15)
            raise
        finally:
            state.update(elapsed_seconds=time.monotonic() - tick,
                frozen_candidate=manifest(BASE) == files, finished_utc=datetime.now(timezone.utc).isoformat())
            save(OUT / 'state.json', state)
    assert state['frozen_candidate']
    assert all(digest(ROOT / p) == h for p, h in prep['sources'].items())
    print(json.dumps(state), flush=True)


if __name__ == '__main__':
    run()
