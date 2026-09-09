"""Bounded serial quality, package and short-game screen; never selects a release."""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.feedback_matches_windows import feedback_path
from scripts.overnight_geometry_trial import ROOT, check_stop, digest, manifest, save

BASE = ROOT / 'runs/overnight-20260909/coalesced-search-01/prototype'

FAILURES = {'flag', 'illegal', 'crash', 'init', 'both_failed'}
OPENINGS = 'configs/overnight-september9-short-openings.json'


def clean_win(game):
    return game['score'] == 1 and game['termination'] not in FAILURES and game.get('failed_colour') is None


def comparison_passes(games):
    return (len(games) == 4 and sum(g['score'] for g in games) >= 2
        and any(clean_win(g) for g in games)
        and all(g['termination'] not in FAILURES and g.get('failed_colour') is None for g in games))


def advance(games):
    return (len(games) == 2 and {g['candidate_white'] for g in games} == {True, False}
            and any(clean_win(g) for g in games)
            and all(g['termination'] not in FAILURES and g.get('failed_colour') is None for g in games))


def audit_feedback(result_path):
    from scripts.overnight_matches import audited
    from training.game_feedback import normalise_game

    result_path = feedback_path(result_path)
    result = audited(result_path)
    root = result_path.parent / 'postgame-feedback'
    for game in result['games']:
        _, identity = normalise_game(game)
        marker = json.loads((root / 'completed' / (identity['game_key'] + '.json')).read_text(encoding='utf-8'))
        assert digest(root / marker['training']) == marker['training_sha256']
        assert json.loads((root / marker['review']).read_text(encoding='utf-8'))['status'] == 'complete'
    return result


def run(directory):
    from scripts.overnight_capacity import wait_for_capacity

    directory = directory.resolve()
    assert directory.is_relative_to(ROOT / 'runs/overnight-20260909')
    prep = json.loads((directory / 'preparation.json').read_text(encoding='utf-8'))
    trial = json.loads((directory / 'state.json').read_text(encoding='utf-8'))
    assert trial['status'] == 'complete' and trial['passed'] and trial['frozen_candidates']
    out = directory / 'candidate-screen-01'
    assert not out.exists(), 'Preserve partial or completed screens; no implicit retry'
    out.mkdir()
    candidate = prep['candidates']['prototype']
    assert (ROOT / prep['candidates']['baseline']).resolve() == BASE.resolve()
    package = directory / 'prototype.zip'
    assert package.exists()
    frozen = prep['candidate_files']
    source_paths = [Path(__file__), ROOT / OPENINGS, ROOT / 'scripts/overnight_clock_quality.py',
        ROOT / 'scripts/validate_package_staged_fixed.py', ROOT / 'scripts/validate_package.py',
        ROOT / 'scripts/feedback_matches.py', ROOT / 'scripts/feedback_matches_windows.py',
        ROOT / 'docs/OVERNIGHT_PORTABLE_SCREEN_20260909.md', ROOT / 'training/game_feedback.py',
        ROOT / 'training/reward_policy.py', ROOT / 'scripts/overnight_game.py']
    sources = {str(p.relative_to(ROOT)): digest(p) for p in source_paths}
    report = dict(status='running', candidate=candidate, baseline=str(BASE.relative_to(ROOT)),
        trial_sha256=digest(directory / 'state.json'), package_sha256=digest(package),
        source_files=sources, stages=[], matches=[], provisional_comparison_passed=False,
        scope='Serial screen versus compiler-repaired v1.53 control, not exact selected v1.53 ZIP. Earlier failures stay recorded. No release selection, automatic competition upload or calibrated Elo.')
    save(out / 'state.json', report)

    def verify():
        assert all(manifest(ROOT / p) == frozen[label] for label, p in prep['candidates'].items())
        assert all(digest(ROOT / p) == h for p, h in sources.items())
        assert digest(package) == report['package_sha256']

    def stage(name, args, budget):
        check_stop()
        verify()
        # Reserve the full bounded stage before the heavy-work cutoff.
        remaining = (datetime(2026, 9, 9, 5, 40, tzinfo=timezone.utc) - datetime.now(timezone.utc)).total_seconds()
        if remaining < budget:
            raise InterruptedError(f'Insufficient overnight time for bounded stage {name}')
        wait_for_capacity(out / f'{name}-capacity.json', minimum_memory_mb=1400, wait_seconds=120)
        record = dict(stage=name, status='running', args=args, timeout_seconds=budget)
        report['stages'].append(record)
        save(out / 'state.json', report)
        tick = time.monotonic()
        with (out / f'{name}.log').open('w', encoding='utf-8') as log:
            process = subprocess.Popen([sys.executable, '-X', 'utf8', '-m', *args], cwd=ROOT,
                stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            record['pid'] = process.pid
            save(out / 'state.json', report)
            try:
                while process.poll() is None:
                    if any(p.exists() for p in (ROOT / 'STOP_TRAINING', ROOT / 'STOP_BENCHMARK', directory.parent / 'STOP')):
                        raise InterruptedError('User stop flag')
                    if time.monotonic() - tick > budget:
                        raise TimeoutError(f'{name} exceeded its bounded stage budget')
                    time.sleep(.5)
                assert process.returncode == 0, f'{name} exit {process.returncode}; preserved log'
                record['status'] = 'complete'
            except BaseException as error:
                record.update(status='failed', error=repr(error))
                if process.poll() is None:
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                            capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    else:
                        process.kill()
                    process.wait(timeout=15)
                raise
            finally:
                record['elapsed_seconds'] = time.monotonic() - tick
                save(out / 'state.json', report)
        verify()

    def match(label, stage_name, pairs, offset, levels=None):
        cycle = f'overnight9-{directory.name}-{label}'
        args = ['scripts.feedback_matches_windows', '--candidate', candidate, '--opponent', str(BASE.relative_to(ROOT)),
            '--stage', stage_name, '--pairs', str(pairs), '--offset', str(offset), '--cycle', cycle,
            '--openings', OPENINGS]
        if levels:
            args += ['--levels', *map(str, levels)]
        stage(label, args, 5400 if stage_name == 'comparison' else 2700)
        path = ROOT / 'runs/improvement-loop-20260907' / cycle / f'{stage_name}-{Path(candidate).name}/results.json'
        result = audit_feedback(path)
        report['matches'].append(dict(label=label, result_path=str(path.relative_to(ROOT)),
            sha256=digest(path), summary=result['summary']))
        save(out / 'state.json', report)
        return result['games']

    try:
        stage('clock-quality', ['scripts.overnight_clock_quality', '--run', str(directory)], 900)
        quality_path = directory / 'clock-quality-01/state.json'
        quality = json.loads(quality_path.read_text(encoding='utf-8'))
        report['quality_sha256'] = digest(quality_path)
        if quality['status'] != 'complete' or not quality['passed'] or not quality['frozen_candidates']:
            report.update(status='complete', decision='reject_clock_quality')
            return
        validation = out / 'validation.json'
        stage('read-only', ['scripts.validate_package_staged_fixed', '--zip', str(package), '--out', str(validation)], 180)
        checked = json.loads(validation.read_text(encoding='utf-8'))
        assert checked['status'] == 'complete' and checked['sha256'] == report['package_sha256']
        games = match('comparison', 'comparison', 2, 0)
        passed = comparison_passes(games)
        report['provisional_comparison_passed'] = passed
        if not passed:
            report.update(status='complete', decision='reject_short_comparison')
            return
        for level in (2400, 2600, 2800, 3000):
            games = match(f'rated-{level}', 'rated', 1, 2, [level])
            if not advance(games):
                break
        report.update(status='complete', decision='review_all_game_evidence_before_release_selection')
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        report['completed_utc'] = datetime.now(timezone.utc).isoformat()
        report['frozen_candidates'] = all(manifest(ROOT / p) == frozen[label] for label, p in prep['candidates'].items())
        if not report['frozen_candidates']:
            report.update(status='failed', error='Frozen candidate mutated')
        save(out / 'state.json', report)
        print(json.dumps({k:v for k,v in report.items() if k not in ('source_files','stages')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    run(parser.parse_args().run)
