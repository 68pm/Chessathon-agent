"""Bounded eight-game daytime comparison; review all games and keep playing files frozen."""

import argparse
import json
import os
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from scripts.daytime_common import BASE, DEADLINE, ROOT, check_stop, digest, manifest, save
from scripts.overnight_archive_challenge import archive_matches
from scripts.overnight_portable_fast_screen import FAILURES, audit_feedback

SOURCE = ROOT / 'runs/daytime-20260909/pawn-extrema-01'
QUALITY = ROOT / 'runs/daytime-20260909/pawn-quality-01'
OUT = ROOT / 'runs/daytime-20260909/pawn-screen-01'
OLDER = ROOT / 'candidates/compiled-near-queen-checks-v1'
OPENINGS = 'configs/overnight-september9-short-openings.json'


def operationally_clean(games):
    return all(g['termination'] not in FAILURES and g.get('failed_colour') is None for g in games)


def pair_passes(games, minimum):
    return (len(games) == 2 and {g['candidate_white'] for g in games} == {True, False}
            and operationally_clean(games) and sum(g['score'] for g in games) >= minimum)


def qualifies_2800(games):
    return pair_passes(games, 1) and any(g['score'] == 1 for g in games)


def prepare():
    check_stop()
    assert not OUT.exists(), 'Preserve consumed attempts.'
    for directory in (SOURCE, QUALITY):
        state = json.loads((directory / 'state.json').read_text())
        assert state['status'] == 'complete' and state['passed'] and state['frozen_candidates']
        assert json.loads((directory / 'supervisor.json').read_text())['status'] == 'complete'
    original = json.loads((SOURCE / 'preparation.json').read_text())
    candidate = ROOT / original['candidates']['prototype']
    assert all(manifest(ROOT / p) == original['candidate_files'][label]
               for label, p in original['candidates'].items())
    archives = {'v1.42': ROOT.parent / 'chessity-agent-v1.42.zip',
                'v1.53': ROOT.parent / 'chessity-agent-v1.53.zip'}
    archive_matches(archives['v1.42'], BASE)
    archive_matches(archives['v1.53'], OLDER)
    OUT.mkdir()
    package = OUT / 'pawn-extrema-candidate.zip'
    with zipfile.ZipFile(package, 'x', zipfile.ZIP_DEFLATED) as zipped:
        for name in manifest(candidate):
            zipped.write(candidate / name, name)
    archive_matches(package, candidate)
    paths = [Path(__file__), ROOT / 'scripts/daytime_common.py',
        ROOT / 'tests/test_daytime_candidate_screen.py', ROOT / 'docs/DAYTIME_PAWN_SCREEN_20260909.md',
        ROOT / OPENINGS, ROOT / 'configs/overnight-opponent-pool.json',
        ROOT / 'scripts/feedback_matches.py', ROOT / 'scripts/feedback_matches_windows.py',
        ROOT / 'scripts/overnight_matches.py', ROOT / 'scripts/overnight_game.py',
        ROOT / 'scripts/overnight_portable_fast_screen.py', ROOT / 'scripts/overnight_archive_challenge.py',
        ROOT / 'scripts/validate_package_staged_fixed.py', ROOT / 'scripts/validate_package.py',
        ROOT / 'training/game_feedback.py', ROOT / 'training/reward_policy.py',
        SOURCE / 'state.json', SOURCE / 'preparation.json', QUALITY / 'state.json']
    save(OUT / 'preparation.json', dict(created_utc=datetime.now(timezone.utc).isoformat(),
        candidate=str(candidate.relative_to(ROOT)),
        files={str(p.relative_to(ROOT)): manifest(p) for p in (candidate, BASE, OLDER)},
        archives={str(p.relative_to(ROOT.parent)): digest(p) for p in archives.values()},
        package_sha256=digest(package), source_sha256={str(p.relative_to(ROOT)): digest(p) for p in paths},
        matches=[dict(label='versus42', opponent=str(BASE.relative_to(ROOT)), offset=0),
                 dict(label='versus53', opponent=str(OLDER.relative_to(ROOT)), offset=1),
                 dict(label='rated2400', level=2400, offset=2),
                 dict(label='rated2600', level=2600, offset=2)],
        qualification='Both colours; >=1.5/2 vs exact42 and >=1/2 vs exact53, no operational failures. Both rated pairs reviewed; 2800 pair only after a clean played2600 win.',
        scope='Small development screen. No calibrated Elo, automatic model selection or live submission inside this runner.'))
    print('Prepared frozen eight-game screen with conditional 2800 pair.', flush=True)


def run():
    from scripts.overnight_capacity import wait_for_capacity

    prep = json.loads((OUT / 'preparation.json').read_text())
    assert not (OUT / 'state.json').exists(), 'Consumed screen; preserve previous state.'
    package = OUT / 'pawn-extrema-candidate.zip'
    report = dict(status='running', stages=[], matches=[], passed=False, package_sha256=prep['package_sha256'])
    save(OUT / 'state.json', report)

    def verify():
        assert all(manifest(ROOT / p) == h for p, h in prep['files'].items())
        assert all(digest(ROOT / p) == h for p, h in prep['source_sha256'].items())
        assert all(digest(ROOT.parent / p) == h for p, h in prep['archives'].items())
        assert digest(package) == prep['package_sha256']

    def stage(label, arguments, budget):
        check_stop()
        verify()
        assert (DEADLINE - datetime.now(timezone.utc)).total_seconds() > budget + 120, 'Daytime stage cannot finish before cutoff'
        wait_for_capacity(OUT / (label + '-capacity.json'), minimum_memory_mb=1400, wait_seconds=120)
        row = dict(label=label, status='running', arguments=arguments, timeout_seconds=budget)
        report['stages'].append(row)
        tick = time.monotonic()
        with (OUT / (label + '.log')).open('w', encoding='utf-8') as log:
            process = subprocess.Popen([sys.executable, '-X', 'utf8', '-m', *arguments], cwd=ROOT,
                stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            row['pid'] = process.pid
            save(OUT / 'state.json', report)
            try:
                while process.poll() is None:
                    check_stop()
                    if time.monotonic() - tick > budget:
                        raise TimeoutError(f'{label} exceeded declared bound')
                    time.sleep(.5)
                assert process.returncode == 0, f'{label} exited {process.returncode}; inspect preserved log'
                row['status'] = 'complete'
            except BaseException as error:
                row.update(status='failed', error=repr(error))
                if process.poll() is None:
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                        capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    process.wait(timeout=15)
                raise
            finally:
                row['elapsed_seconds'] = time.monotonic() - tick
                save(OUT / 'state.json', report)
        verify()

    def match(row):
        stage_name = 'rated' if 'level' in row else 'comparison'
        cycle = 'd9-pawn-01-' + row['label']
        arguments = ['scripts.feedback_matches_windows', '--candidate', prep['candidate'],
            '--stage', stage_name, '--pairs', '1', '--offset', str(row['offset']),
            '--cycle', cycle, '--openings', OPENINGS]
        arguments += ['--levels', str(row['level'])] if 'level' in row else ['--opponent', row['opponent']]
        stage(row['label'], arguments, 1500)
        path = ROOT / 'runs/improvement-loop-20260907' / cycle / f'{stage_name}-{Path(prep["candidate"]).name}/results.json'
        result = audit_feedback(path)
        report['matches'].append(dict(**row, result_path=str(path.relative_to(ROOT)),
            sha256=digest(path), summary=result['summary']))
        save(OUT / 'state.json', report)
        return result['games']

    try:
        stage('read-only', ['scripts.validate_package_staged_fixed', '--zip', str(package),
              '--out', str(OUT / 'validation.json')], 180)
        validation = json.loads((OUT / 'validation.json').read_text())
        assert validation['status'] == 'complete' and validation['sha256'] == prep['package_sha256']
        played = {}
        for row in prep['matches']:
            played[row['label']] = match(row)
            if not operationally_clean(played[row['label']]):
                report.update(status='complete', decision='stop_and_diagnose_operational_failure')
                return
        if qualifies_2800(played['rated2600']):
            played['rated2800'] = match(dict(label='rated2800', level=2800, offset=2))
        report['passed'] = (pair_passes(played['versus42'], 1.5) and pair_passes(played['versus53'], 1)
            and all(operationally_clean(games) for games in played.values()))
        report.update(status='complete', decision='review_for_qualified_release_and_authorised_upload'
                      if report['passed'] else 'retain_v142_and_diagnose')
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        report['finished_utc'] = datetime.now(timezone.utc).isoformat()
        report['frozen_candidates'] = all(manifest(ROOT / p) == h for p, h in prep['files'].items())
        if not report['frozen_candidates']:
            report.update(status='failed', passed=False, error='Playing files changed')
        save(OUT / 'state.json', report)
        print(json.dumps({k: v for k, v in report.items() if k != 'stages'}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    prepare() if args.prepare else run()
