"""Run the registered fixed study once, retaining all outcomes without adaptation."""

import concurrent.futures
import ctypes
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

from scripts.alien_rating_ladder import save_json, sha256
from scripts.fastchess_matches import run_game, score_summary
from scripts.magnus_benchmark import SF, manifest
from scripts.prepare_consistency_study import ARCHIVE_SHA, CANDIDATE, OUT, stopped
from scripts.record_fastchess import audit_game
from training.fastchess_data import ROOT

SOURCE_FILES = ['scripts/run_consistency_study.py', 'scripts/review_consistency_study.py',
                'scripts/prepare_consistency_study.py', 'scripts/improvement_consistency.py',
                'scripts/fastchess_matches.py', 'scripts/record_fastchess.py',
                'harness/sandbox.py', 'harness/runner.py', 'harness/rules.py']


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    state_path, report_path = OUT / 'controller.json', OUT / 'results.json'
    if state_path.exists() or report_path.exists():
        raise ValueError('Never silently restart or reuse interrupted confirmation results.')
    stopped()
    study = read(OUT / 'study.json')
    preparation = read(OUT / 'preparation.json')
    assert preparation['status'] == 'complete' and preparation['study_sha256'] == sha256(OUT / 'study.json')
    assert study['teacher_preparation_complete'] and len(study['schedule']) == 256
    assert study['files'] == {CANDIDATE:manifest(ROOT / CANDIDATE)}
    assert sha256((ROOT / CANDIDATE).with_suffix('.zip')) == ARCHIVE_SHA == study['candidate_sha256']
    assert study['stockfish_sha256'] == sha256(SF)
    for name, expected in study['source_sha256'].items():
        assert sha256(ROOT / name) == expected
    assert study['starts_sha256'] == sha256(OUT / 'starts.json')
    assert study['exposure_sha256'] == sha256(OUT / 'prior-exposure.json')
    assert study['balance_sha256'] == sha256(OUT / 'balance-attempts.json')
    readonly = ROOT / 'runs/improvement-loop-20260907/compiled-qsearch-endgames-v1-readonly.json'
    check = read(readonly)
    assert check['sha256'] == ARCHIVE_SHA and all(v == 'blocked' for v in check['read_only_checks'].values())
    pool_path = ROOT / 'configs/improvement-opponent-pool.json'
    pool = read(pool_path)
    assert pool['active_nominal_levels'] == [2400,2600] and pool['qualification_attempts'] == []
    registered = datetime.now(timezone.utc).isoformat()
    pool['qualification_attempts'] = [dict(attempt=study['attempts'][str(level)], nominal_level=level,
        candidate=CANDIDATE, candidate_sha256=ARCHIVE_SHA, study='consistency-01',
        status='registered', registered_utc=registered, games=128, blocks=2,
        study_sha256=sha256(OUT / 'study.json')) for level in [2400,2600]]
    pool['qualification_status'] = 'Independent256-game v1.41 study registered. Neither level qualifies before all games and independent audit complete.'
    save_json(pool_path, pool)
    save_json(OUT / 'registration.json', pool)
    sources = {p:sha256(ROOT / p) for p in SOURCE_FILES}
    report = dict(status='running', config=study['config'], schedule=study['schedule'], games=[],
        files=study['files'], source_files=sources, stockfish_sha256=study['stockfish_sha256'],
        pool_sha256=sha256(pool_path), study_sha256=sha256(OUT / 'study.json'),
        readonly_sha256=sha256(readonly), started_utc=registered, interruptions=[],
        scope=study['scope'], runtime_contract='One engine thread per process; at most two games; original120+0.5 runner; no learning or teacher analysis.')
    state = dict(status='running', stage='fixed_matches', pid=os.getpid(), started_utc=registered,
                 completed_games=0, total_games=256, report=str(report_path.relative_to(ROOT)))
    lock = OUT / 'controller.lock'
    handle = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.write(handle, str(os.getpid()).encode())
    os.close(handle)
    save_json(state_path, state)
    save_json(report_path, report)
    if os.name == 'nt':
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            for index in range(0, len(study['schedule']), 2):
                stopped()
                assert sources == {p:sha256(ROOT / p) for p in sources}
                pair = study['schedule'][index:index + 2]
                futures = [executor.submit(run_game, job, study['config'], OUT) for job in pair]
                for future in concurrent.futures.as_completed(futures):
                    row = future.result()
                    audit_game(row, study['config'])
                    report['games'].append(row)
                    report['games'].sort(key=lambda r:r['id'])
                    report['summary'] = score_summary(report['games'])
                    save_json(report_path, report)
                    state.update(completed_games=len(report['games']), summary=report['summary'],
                                 updated_utc=datetime.now(timezone.utc).isoformat())
                    save_json(state_path, state)
                    print(f"{len(report['games'])}/256: block{row['block']} {row['family']} {row['score']} {row['termination']}", flush=True)
        assert study['files'] == {CANDIDATE:manifest(ROOT / CANDIDATE)}
        assert report['pool_sha256'] == sha256(pool_path)
        assert sources == {p:sha256(ROOT / p) for p in sources}
        report.update(status='complete', completed_utc=datetime.now(timezone.utc).isoformat())
        save_json(report_path, report)
        state.update(stage='independent_audit', completed_games=256)
        save_json(state_path, state)
        with (OUT / 'review.log').open('w', encoding='utf-8') as log:
            subprocess.run([sys.executable, '-m', 'scripts.review_consistency_study'], cwd=ROOT,
                           stdout=log, stderr=subprocess.STDOUT, check=True,
                           creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        state.update(status='complete', stage='results_ready', review='consistency-review.json',
                     completed_utc=datetime.now(timezone.utc).isoformat())
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        if report['status'] != 'complete':
            report.update(status='failed', error=repr(error))
            report['interruptions'].append(dict(utc=datetime.now(timezone.utc).isoformat(), reason=repr(error)))
            save_json(report_path, report)
        raise
    finally:
        save_json(state_path, state)
        lock.unlink()
        if os.name == 'nt':
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == '__main__':
    main()
