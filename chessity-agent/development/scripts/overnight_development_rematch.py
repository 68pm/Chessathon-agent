"""One bounded development ladder for fresh, fully reviewed 120+.5 games."""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone

from scripts.overnight_candidate_screen import FAILURES, OPENINGS, audit_feedback
from scripts.overnight_capacity import wait_for_capacity
from scripts.overnight_geometry_trial import ROOT, check_stop, digest, manifest, save

OUT = ROOT / 'runs/overnight-20260909/development-rematch-01'
CANDIDATE = ROOT / 'runs/overnight-20260909/coalesced-search-01/prototype'
DEADLINE = datetime(2026, 9, 9, 5, 40, tzinfo=timezone.utc)
LEVELS = (2400, 2600, 2800, 3000)
PAIR_BUDGET = 2700


def unlock_next(games):
    return (len(games) == 2 and {g['candidate_white'] for g in games} == {True, False}
            and all(g['termination'] not in FAILURES and g.get('failed_colour') is None for g in games)
            and any(g['score'] == 1 for g in games))


def remaining_budget(now):
    return (DEADLINE - now).total_seconds() >= PAIR_BUDGET


def run():
    check_stop()
    assert not OUT.exists(), 'Preserve completed or interrupted runs; no implicit replay.'
    OUT.mkdir()
    source_paths = [__file__, ROOT / OPENINGS, ROOT / 'scripts/feedback_matches.py',
        ROOT / 'scripts/overnight_matches.py', ROOT / 'scripts/overnight_game.py',
        ROOT / 'training/game_feedback.py', ROOT / 'training/reward_policy.py',
        ROOT / 'scripts/overnight_candidate_screen.py']
    sources = {str(p.relative_to(ROOT)): digest(p) for p in map(type(ROOT), source_paths)}
    frozen = manifest(CANDIDATE)
    report = dict(status='running', candidate=str(CANDIDATE.relative_to(ROOT)),
        candidate_files=frozen, source_files=sources, levels=list(LEVELS),
        pair_budget_seconds=PAIR_BUDGET, opening_offset=2, stages=[], matches=[],
        started_utc=datetime.now(timezone.utc).isoformat(),
        attribution='v1.53 search logic and weights with compiler signature repair; not the selected v1.53 ZIP.',
        scope='Predeclared bounded development diagnostic. Earlier failed clock-quality and efficiency gates remain failed. No release promotion or calibrated Elo claim. Every game reviewed; separate experimental checkpoints only.')
    save(OUT / 'state.json', report)

    def verify():
        assert manifest(CANDIDATE) == frozen, 'Playing candidate changed.'
        assert all(digest(ROOT / p) == h for p, h in sources.items()), 'Frozen runner source changed.'

    try:
        for level in LEVELS:
            check_stop()
            verify()
            if not remaining_budget(datetime.now(timezone.utc)):
                report.update(status='complete', decision='stop_before_deadline')
                break
            wait_for_capacity(OUT / f'{level}-capacity.json', minimum_memory_mb=1400, wait_seconds=120)
            check_stop()
            if not remaining_budget(datetime.now(timezone.utc)):
                report.update(status='complete', decision='stop_before_deadline')
                break
            cycle = f'overnight9-development-rematch-01-{level}'
            args = ['scripts.feedback_matches', '--candidate', str(CANDIDATE.relative_to(ROOT)),
                    '--stage', 'rated', '--pairs', '1', '--offset', '2', '--cycle', cycle,
                    '--openings', OPENINGS, '--levels', str(level)]
            stage = dict(level=level, status='running', args=args)
            report['stages'].append(stage)
            save(OUT / 'state.json', report)
            tick = time.monotonic()
            with (OUT / f'{level}.log').open('w', encoding='utf-8') as log:
                process = subprocess.Popen([sys.executable, '-X', 'utf8', '-m', *args], cwd=ROOT,
                    stdout=log, stderr=subprocess.STDOUT,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
                stage['pid'] = process.pid
                save(OUT / 'state.json', report)
                try:
                    while process.poll() is None:
                        check_stop()
                        if time.monotonic() - tick > PAIR_BUDGET:
                            raise TimeoutError(f'{level} pair exceeded 45-minute bound.')
                        time.sleep(.5)
                    assert process.returncode == 0, f'{level} match failed; preserve log and saved games.'
                    stage['status'] = 'complete'
                except BaseException as error:
                    stage.update(status='failed', error=repr(error))
                    if process.poll() is None:
                        if os.name == 'nt':
                            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                                capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                        else:
                            process.kill()
                        process.wait(timeout=15)
                    raise
                finally:
                    stage['elapsed_seconds'] = time.monotonic() - tick
                    save(OUT / 'state.json', report)
            verify()
            result_path = ROOT / 'runs/improvement-loop-20260907' / cycle / 'rated-prototype/results.json'
            result = audit_feedback(result_path)
            allowed = unlock_next(result['games'])
            report['matches'].append(dict(level=level, result_path=str(result_path.relative_to(ROOT)),
                sha256=digest(result_path), summary=result['summary'], unlock_next=allowed))
            save(OUT / 'state.json', report)
            if not allowed:
                report.update(status='complete', decision='analyse_this_level_before_further_ascent')
                break
        else:
            report.update(status='complete', decision='bounded_ladder_finished')
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        report['frozen_candidate'] = manifest(CANDIDATE) == frozen
        if not report['frozen_candidate']:
            report.update(status='failed', error='Playing candidate mutated.')
        report['completed_utc'] = datetime.now(timezone.utc).isoformat()
        save(OUT / 'state.json', report)
        print(json.dumps({k: v for k, v in report.items() if k not in ('candidate_files', 'source_files', 'stages')}), flush=True)


if __name__ == '__main__':
    run()
