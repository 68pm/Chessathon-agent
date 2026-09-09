"""Fresh isolated candidate probes on reviewed errors; preserve every attempt."""
import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from scripts import daytime_pawn_extrema as worker_api
from scripts import evening_pawn_threat as quality
from scripts.progression_common import ROOT, RUN, BASE, check_stop, digest, manifest, save

VARIANT = 'pv-guard-01'
OUT = RUN / VARIANT


def prepare():
    from scripts.overnight_archive_challenge import archive_matches
    from scripts.progression_pv_guard_transform import transform
    check_stop()
    assert VARIANT == 'pv-guard-01' and not OUT.exists()
    archive_matches(ROOT.parent / 'chessity-agent-v1.56.zip', BASE)
    previous = ROOT / 'runs/evening-20260909/development-targets.json'
    rows = json.loads(previous.read_text())['rows']
    choices = [('versus56-b12-game-2', 9), ('versus56-b12-game-2', 21),
        ('versus56-b12-game-2', 35), ('versus56-b12-game-2', 36),
        ('versus56-d48-game-1', 30), ('versus56-d48-game-2', 24)]
    roots = []
    for game, move in choices:
        matching = [r for r in rows if r['game'] == game and r['fullmove'] == move]
        assert len(matching) == 1
        row = matching[0]
        roots.append(dict(id=f'{game}-move{move}', **{k: row[k] for k in ('fen', 'start_fen', 'history')}))
    old = ROOT / 'runs/evening-20260909/pawn-threat-01/preparation.json'
    roots += json.loads(old.read_text())['roots'][:6]
    assert len(roots) == len({r['fen'] for r in roots}) == 12
    prototype = OUT / 'prototype'
    shutil.copytree(BASE, prototype, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    source = transform((BASE / 'engine/compiled_core.py').read_text())
    (prototype / 'engine/compiled_core.py').write_text(source, encoding='utf-8', newline='\n')
    experiment = ROOT / 'experiments/progression_pv_guard_core.py'
    assert not experiment.exists()
    experiment.write_text(source, encoding='utf-8', newline='\n')
    paths = [Path(__file__), Path(quality.__file__), Path(worker_api.__file__),
        ROOT / 'scripts/progression_common.py', ROOT / 'scripts/progression_pv_guard_transform.py',
        experiment, previous, old, ROOT / 'tests/test_progression_pv_guard.py',
        ROOT / 'configs/progression-september9-openings.json', ROOT / 'training/game_feedback.py']
    save(OUT / 'preparation.json', dict(created_utc=datetime.now(timezone.utc).isoformat(),
        candidates={'baseline': str(BASE.relative_to(ROOT)), 'prototype': str(prototype.relative_to(ROOT))},
        candidate_files={'baseline': manifest(BASE), 'prototype': manifest(prototype)}, roots=roots,
        source_sha256={str(p.relative_to(ROOT)): digest(p) for p in paths},
        protocol=dict(clock_seconds=1, order=['baseline', 'prototype', 'prototype', 'baseline'],
            teacher_budgets=[80000, 320000], deep_root=None, deep_budgets=[]),
        scope='Principal-variation depth guard on exact v1.56. Latest local losses and prior competition roots are development data.'))
    env = dict(os.environ, NUMBA_DISABLE_JIT='1', PYTHONUTF8='1', OPENBLAS_NUM_THREADS='1')
    with (OUT / 'tests.log').open('w', encoding='utf-8') as log:
        result = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'pytest', '-q',
            'tests/test_progression_pv_guard.py', '--junitxml', str(OUT / 'tests.xml')],
            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=120,
            creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 0, 'Correctness tests failed; preserve preparation and logs'
    print('Prepared PV-depth-guard candidate with correctness checks', flush=True)


class Worker(worker_api.WarmWorker):
    def __init__(self, label):
        self.label = label
        self.log = (OUT / f'{label}.log').open('w', encoding='utf-8')
        self.answers = queue.Queue()
        self.process = subprocess.Popen([sys.executable, '-X', 'utf8', '-m',
            'scripts.progression_pv_guard', '--variant', VARIANT, '--worker', label],
            cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
            text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW)
        def receive():
            for line in self.process.stdout:
                self.answers.put(line)
            self.answers.put(None)
        threading.Thread(target=receive, daemon=True).start()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--variant', default=VARIANT)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--worker', choices=('baseline', 'prototype'))
    args = parser.parse_args()
    VARIANT = args.variant
    assert VARIANT == 'pv-guard-01'
    OUT = RUN / VARIANT
    if args.prepare:
        prepare()
    elif args.worker:
        worker_api.OUT, worker_api.check_stop = OUT, check_stop
        worker_api.worker(args.worker)
    else:
        quality.OUT, quality.Worker, quality.check_stop = OUT, Worker, check_stop
        quality.controller()
