"""Validate a frozen reviewed policy candidate before any match qualification."""
import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from scripts import daytime_pawn_extrema as worker_api
from scripts import evening_pawn_threat as quality
from scripts.progression_common import ROOT, RUN, BASE, check_stop, digest, manifest, save

FIT = RUN / 'reward-policy-01'
OUT = RUN / 'reviewed-policy-01'


def prepare():
    from scripts.overnight_archive_challenge import archive_matches
    from scripts.feedback_matches_windows import feedback_path
    from training.game_feedback import normalise_game
    check_stop(); assert not OUT.exists()
    fit = json.loads((FIT / 'state.json').read_text())
    assert fit['status'] == 'complete' and fit['training_objective_improved']
    assert digest(FIT / 'player-policy.npz') == fit['model_sha256']
    archive_matches(ROOT.parent / 'chessity-agent-v1.56.zip', BASE)
    prototype = OUT / 'prototype'
    shutil.copytree(BASE, prototype, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copyfile(FIT / 'player-policy.npz', prototype / 'models/player-policy.npz')
    runtime = json.loads((prototype / 'runtime.json').read_text()); runtime['policy_cp'] = 40
    save(prototype / 'runtime.json', runtime)
    before, after = manifest(BASE), manifest(prototype)
    assert {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)} == {'runtime.json', 'models/player-policy.npz'}
    prior = RUN / 'root-pvs-01/preparation.json'
    roots = json.loads(prior.read_text())['roots'][:11]
    latest = ROOT / 'runs/improvement-loop-20260907/p9-v156-development2400-01/rated-prototype'
    game = json.loads((latest / 'game-001.json').read_text()); _, identity = normalise_game(game)
    feedback = feedback_path(latest / 'postgame-feedback')
    marker = json.loads((feedback / 'completed' / (identity['game_key'] + '.json')).read_text())
    review_path = feedback / marker['review']; review = json.loads(review_path.read_text())
    row, = [r for r in review['rows'] if r['fullmove'] == 35]
    roots.append(dict(id='v156-development2400-white-move35', **{k: row[k] for k in ('start_fen', 'history', 'fen')}))
    assert len(roots) == len({r['fen'] for r in roots}) == 12
    paths = [Path(__file__), Path(quality.__file__), Path(worker_api.__file__),
        ROOT / 'scripts/progression_common.py', ROOT / 'tests/test_progression_reviewed_policy.py',
        ROOT / 'configs/progression-september9-openings.json', FIT / 'preparation.json',
        FIT / 'state.json', FIT / 'player-policy.npz', prior, review_path, ROOT / 'training/game_feedback.py']
    save(OUT / 'preparation.json', dict(candidates={'baseline': str(BASE.relative_to(ROOT)), 'prototype': str(prototype.relative_to(ROOT))},
        candidate_files={'baseline': before, 'prototype': after}, roots=roots,
        source_sha256={str(p.relative_to(ROOT)) if not str(p).startswith('\\\\?\\') else str(p): digest(p) for p in paths},
        protocol=dict(clock_seconds=1, order=['baseline', 'prototype', 'prototype', 'baseline'],
            teacher_budgets=[80000, 320000], deep_root=None, deep_budgets=[]),
        scope='Six reviewed-game policy fit with40cp maximum preference. Exposed development roots only; '
              'no searched-position value change or independent Elo claim.'))
    env = dict(os.environ, OPENBLAS_NUM_THREADS='1', NUMBA_DISABLE_JIT='1', PYTHONUTF8='1')
    with (OUT / 'tests.log').open('w', encoding='utf-8') as log:
        r = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'pytest', '-q',
            'tests/test_progression_reviewed_policy.py', '--junitxml', str(OUT / 'tests.xml')],
            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW)
    assert r.returncode == 0
    print('Prepared frozen reviewed-policy candidate', flush=True)


class Worker(worker_api.WarmWorker):
    def __init__(self, label):
        self.label = label
        self.log = (OUT / f'{label}.log').open('w', encoding='utf-8')
        self.answers = queue.Queue()
        self.process = subprocess.Popen([sys.executable, '-X', 'utf8', '-m',
            'scripts.progression_policy_quality', '--worker', label], cwd=ROOT,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
            text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW)
        def receive():
            for line in self.process.stdout:
                self.answers.put(line)
            self.answers.put(None)
        threading.Thread(target=receive, daemon=True).start()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--worker', choices=('baseline', 'prototype'))
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.worker:
        worker_api.OUT, worker_api.check_stop = OUT, check_stop
        worker_api.worker(args.worker)
    else:
        quality.OUT, quality.Worker, quality.check_stop = OUT, Worker, check_stop
        quality.controller()
