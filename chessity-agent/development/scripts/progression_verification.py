"""Fresh isolated candidate probes on reviewed errors; preserve every attempt."""
import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from scripts import daytime_pawn_extrema as worker_api
from scripts import evening_pawn_threat as quality
from scripts.progression_common import ROOT, RUN, BASE, check_stop, digest, manifest, save

VARIANT = 'root-verification-01'
OUT = RUN / VARIANT


def prepare():
    from scripts.overnight_archive_challenge import archive_matches
    from scripts.progression_verification_transform import core_transform, driver_transform
    check_stop()
    assert VARIANT == 'root-verification-01' and not OUT.exists()
    archive_matches(ROOT.parent / 'chessity-agent-v1.56.zip', BASE)
    previous = ROOT / 'runs/evening-20260909/development-targets.json'
    rows = json.loads(previous.read_text())['rows']
    choices = [('versus56-b12-game-2', 9), ('versus56-b12-game-2', 21),
        ('versus56-b12-game-2', 35), ('versus56-b12-game-2', 36),
        ('versus56-d48-game-1', 30), ('versus56-d48-game-2', 24)]
    root_source = RUN / 'reviewed-policy-01/preparation.json'
    roots = json.loads(root_source.read_text())['roots']
    assert len(roots) == len({r['fen'] for r in roots}) == 12
    old = ROOT / 'runs/evening-20260909/pawn-threat-01/preparation.json'
    prototype = OUT / 'prototype'
    shutil.copytree(BASE, prototype, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    source = core_transform((BASE / 'engine/compiled_core.py').read_text())
    (prototype / 'engine/compiled_core.py').write_text(source, encoding='utf-8', newline='\n')
    experiment = ROOT / 'experiments/progression_verification_core.py'
    assert not experiment.exists()
    experiment.write_text(source, encoding='utf-8', newline='\n')
    driver_source = driver_transform((BASE / 'engine/compiled_driver.py').read_text())
    (prototype / 'engine/compiled_driver.py').write_text(driver_source, encoding='utf-8', newline='\n')
    experiment_driver = ROOT / 'experiments/progression_verification_driver.py'
    assert not experiment_driver.exists()
    experiment_driver.write_text(driver_source.replace('from . import compiled_core as core',
        'from experiments import progression_verification_core as core'), encoding='utf-8', newline='\n')
    paths = [Path(__file__), Path(quality.__file__), Path(worker_api.__file__),
        ROOT / 'scripts/progression_common.py', ROOT / 'scripts/progression_verification_transform.py',
        experiment, experiment_driver, root_source, previous, old, ROOT / 'tests/test_progression_verification.py',
        ROOT / 'configs/progression-september9-openings.json', ROOT / 'training/game_feedback.py']
    save(OUT / 'preparation.json', dict(created_utc=datetime.now(timezone.utc).isoformat(),
        candidates={'baseline': str(BASE.relative_to(ROOT)), 'prototype': str(prototype.relative_to(ROOT))},
        candidate_files={'baseline': manifest(BASE), 'prototype': manifest(prototype)}, roots=roots,
        source_sha256={str(p.relative_to(ROOT)): digest(p) for p in paths},
        protocol=dict(clock_seconds=1, soft_fraction=.6, order=['baseline', 'prototype', 'prototype', 'baseline'],
            teacher_budgets=[80000, 320000], deep_root=None, deep_budgets=[]),
        scope='Bounded three-move root verification using remaining clock reserve. Both controls get1s hard/.6s soft; full-root depth and selective verification depth remain separate. Development only.'))
    env = dict(os.environ, NUMBA_DISABLE_JIT='1', PYTHONUTF8='1', OPENBLAS_NUM_THREADS='1')
    with (OUT / 'tests.log').open('w', encoding='utf-8') as log:
        result = subprocess.run([sys.executable, '-X', 'utf8', '-m', 'pytest', '-q',
            'tests/test_progression_verification.py', '--junitxml', str(OUT / 'tests.xml')],
            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=120,
            creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 0, 'Correctness tests failed; preserve preparation and logs'
    print('Prepared bounded root-verification candidate with correctness checks', flush=True)


def worker(label):
    prep = json.loads((OUT / 'preparation.json').read_text(encoding='utf-8'))
    candidate = ROOT / prep['candidates'][label]
    sys.path.insert(0, str(candidate))
    # Production agent establishes Numba/platform settings before any engine import.
    tick = time.perf_counter()
    import chess

    import agent

    init = time.perf_counter() - tick
    assert Path(sys.modules['engine.compiled_core'].__file__).resolve() == candidate / 'engine/compiled_core.py'
    print(json.dumps(dict(status='ready', init_seconds=init)), flush=True)
    for line in sys.stdin:
        request = json.loads(line)
        if request.get('stop'):
            return
        row = prep['roots'][request['root']]
        check_stop()
        board = chess.Board(row['start_fen'])
        for move in row['history']:
            board.push_uci(move)
        assert board.fen() == row['fen']
        history = board.move_stack.copy()
        for key in ('ttkey', 'ttcontext', 'ttdata', 'killers', 'history'):
            getattr(agent._search, key).fill(0)
        fixed = request['regime'] == 'fixed'
        seconds = 12. if fixed else 1.
        cpu = time.process_time()
        result = agent._search.run(board, seconds, .6 * seconds, max_depth=64,
                                   max_nodes=250000 if fixed else 2**60)
        cpu = time.process_time() - cpu
        assert result.move in board.legal_moves
        assert board.fen() == row['fen'] and board.move_stack == history
        assert result.elapsed <= seconds + .3
        print(json.dumps(dict(**request, id=row['id'], label=label, uci=result.move.uci(),
            score=result.score, depth=result.depth, nodes=result.nodes, seconds=result.elapsed,
            cpu_seconds=cpu, verified_depth=getattr(result,"verified_depth",0))), flush=True)


class Worker(worker_api.WarmWorker):
    def __init__(self, label):
        self.label = label
        self.log = (OUT / f'{label}.log').open('w', encoding='utf-8')
        self.answers = queue.Queue()
        self.process = subprocess.Popen([sys.executable, '-X', 'utf8', '-m',
            'scripts.progression_verification', '--variant', VARIANT, '--worker', label],
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
    assert VARIANT == 'root-verification-01'
    OUT = RUN / VARIANT
    if args.prepare:
        prepare()
    elif args.worker:
        worker_api.OUT, worker_api.check_stop = OUT, check_stop
        worker(args.worker)
    else:
        quality.OUT, quality.Worker, quality.check_stop = OUT, Worker, check_stop
        quality.controller()
