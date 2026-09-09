"""Short exact-archive comparison with feedback and conditional rated ascent."""

import argparse
import json
import os
import subprocess
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from scripts.overnight_geometry_trial import ROOT, check_stop, digest, manifest, save
from scripts.overnight_portable_fast_screen import advance, audit_feedback, clean_win

OUT = ROOT / 'runs/overnight-20260909/archive-challenge-01'
CHALLENGER = 'candidates/compiled-reductions-v1'
SELECTED = 'candidates/compiled-near-queen-checks-v1'
OPENINGS = 'configs/overnight-september9-short-openings.json'
ARCHIVE = ROOT.parent.parent / 'work/github-chessity/chessity-agent/versions/v1.42/chessity-agent-v1.42.zip'
DEADLINE = datetime(2026, 9, 9, 5, 40, tzinfo=timezone.utc)


def archive_matches(archive, folder):
    import hashlib

    with zipfile.ZipFile(archive) as zipped:
        members = {n: hashlib.sha256(zipped.read(n)).hexdigest() for n in zipped.namelist() if not n.endswith('/')}
    assert members == manifest(folder), 'Exact archived source required.'


def prepare():
    assert not OUT.exists(), 'Preserve every challenge.'
    selected_zip = ROOT.parent / 'chessity-agent-v1.53.zip'
    assert digest(ARCHIVE) == '114c1688a63d4039d7965670fcab0891bec24d4835dacafa8698e22d0c01f48b'
    assert digest(selected_zip) == '5747acec37da25ea79704e49d19e45bf23bd2af5842a14eaf66bf6ecf2791315'
    archive_matches(ARCHIVE, ROOT / CHALLENGER)
    archive_matches(selected_zip, ROOT / SELECTED)
    historical_path = ROOT / 'runs/improvement-loop-20260907/cycle-03/rated-compiled-reductions-v1/results.json'
    historical = json.loads(historical_path.read_text(encoding='utf-8'))
    from scripts.overnight_game import score_summary
    from scripts.record_fastchess import audit_game

    assert historical['status'] == 'complete' and len(historical['games']) == 8
    assert historical['files'][CHALLENGER] == manifest(ROOT / CHALLENGER)
    for game in historical['games']:
        audit_game(game, historical['config'])
    summary = score_summary(historical['games'])
    assert any(g['elo'] == 2600 and clean_win(g) for g in historical['games'])
    sources = [Path(__file__), ROOT / 'docs/OVERNIGHT_ARCHIVE_CHALLENGE_20260909.md',
        ROOT / OPENINGS, ROOT / 'scripts/overnight_portable_fast_screen.py',
        ROOT / 'scripts/feedback_matches.py', ROOT / 'scripts/feedback_matches_windows.py',
        ROOT / 'scripts/overnight_matches.py', ROOT / 'scripts/overnight_game.py',
        ROOT / 'scripts/validate_package_staged_fixed.py', ROOT / 'scripts/validate_package.py',
        ROOT / 'training/game_feedback.py', ROOT / 'training/reward_policy.py', historical_path]
    OUT.mkdir()
    save(OUT / 'preparation.json', dict(challenger=CHALLENGER, selected=SELECTED,
        files={p:manifest(ROOT / p) for p in (CHALLENGER, SELECTED)},
        archive_sha256={'v1.42':digest(ARCHIVE), 'v1.53':digest(selected_zip)},
        source_sha256={str(p.relative_to(ROOT)):digest(p) for p in sources}, historical_summary=summary,
        scope='New direct comparison against exactv1.53. Historicalv1.42 results retained separately. No automatic promotion or Elo claim.'))


def run():
    from scripts.overnight_capacity import wait_for_capacity

    prep = json.loads((OUT / 'preparation.json').read_text(encoding='utf-8'))
    assert not (OUT / 'state.json').exists()
    report = dict(status='running', stages=[], matches=[], preparation_sha256=digest(OUT / 'preparation.json'),
        selected_version=None, calibrated_elo=None)
    save(OUT / 'state.json', report)

    def verify():
        assert all(manifest(ROOT / p) == h for p, h in prep['files'].items())
        assert all(digest(ROOT / p) == h for p, h in prep['source_sha256'].items())
        assert digest(ARCHIVE) == prep['archive_sha256']['v1.42']

    def stage(name, arguments, budget):
        check_stop()
        verify()
        if (DEADLINE - datetime.now(timezone.utc)).total_seconds() < budget:
            report.update(status='complete', decision='deadline_before_next_stage', pending_stage=name)
            return False
        wait_for_capacity(OUT / (name + '-capacity.json'), minimum_memory_mb=1400, wait_seconds=120)
        row = dict(stage=name, status='running', arguments=arguments, timeout_seconds=budget)
        report['stages'].append(row)
        save(OUT / 'state.json', report)
        started = time.monotonic()
        with (OUT / (name + '.log')).open('w', encoding='utf-8') as log:
            process = subprocess.Popen([sys.executable, '-X', 'utf8', '-m', *arguments], cwd=ROOT,
                stdout=log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            row['pid'] = process.pid
            save(OUT / 'state.json', report)
            try:
                while process.poll() is None:
                    check_stop()
                    if time.monotonic() - started > budget:
                        raise TimeoutError(f'{name} exceeded predeclared budget')
                    time.sleep(.5)
                assert process.returncode == 0, f'{name} exit{process.returncode}'
                row['status'] = 'complete'
            except BaseException as error:
                row.update(status='failed', error=repr(error))
                if process.poll() is None:
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], check=True,
                            capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    else:
                        process.kill()
                    process.wait(timeout=15)
                raise
            finally:
                row['elapsed_seconds'] = time.monotonic() - started
                save(OUT / 'state.json', report)
        verify()
        return True

    def matches(name, stage_name, pairs, offset, level=None):
        cycle = 'n9-archive-42-' + name
        arguments = ['scripts.feedback_matches_windows', '--candidate', CHALLENGER, '--opponent', SELECTED,
            '--stage', stage_name, '--pairs', str(pairs), '--offset', str(offset), '--cycle', cycle,
            '--openings', OPENINGS]
        if level:
            arguments += ['--levels', str(level)]
        if not stage(name, arguments, 2700 if stage_name == 'comparison' else 1500):
            return None
        path = ROOT / 'runs/improvement-loop-20260907' / cycle / (stage_name + '-compiled-reductions-v1/results.json')
        result = audit_feedback(path)
        report['matches'].append(dict(label=name, result_path=str(path.relative_to(ROOT)),
            sha256=digest(path), summary=result['summary']))
        save(OUT / 'state.json', report)
        return result['games']

    try:
        if not stage('read-only', ['scripts.validate_package_staged_fixed', '--zip', str(ARCHIVE),
            '--out', str(OUT / 'validation.json')], 180):
            return
        validated = json.loads((OUT / 'validation.json').read_text(encoding='utf-8'))
        assert validated['status'] == 'complete' and validated['sha256'] == prep['archive_sha256']['v1.42']
        games = matches('comparison', 'comparison', 2, 0)
        if games is None:
            return
        favourable = (len(games) == 4 and sum(g['score'] for g in games) >= 2.5
            and any(clean_win(g) for g in games)
            and all(g['termination'] not in ('flag', 'illegal', 'crash', 'init', 'both_failed')
                and g.get('failed_colour') is None for g in games))
        report['favourable_comparison'] = favourable
        if not favourable:
            report.update(status='complete', decision='retain_selected_after_short_comparison')
            return
        for level in (2400, 2600, 2800, 3000):
            games = matches('rated-' + str(level), 'rated', 1, 2, level)
            if games is None:
                return
            if not advance(games):
                break
        report.update(status='complete', decision='review_completed_evidence_before_selection')
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        report['completed_utc'] = datetime.now(timezone.utc).isoformat()
        report['frozen_candidates'] = all(manifest(ROOT / p) == h for p, h in prep['files'].items())
        save(OUT / 'state.json', report)
        print(json.dumps({k:v for k,v in report.items() if k != 'stages'}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    prepare() if parser.parse_args().prepare else run()
