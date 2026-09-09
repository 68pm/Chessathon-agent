"""Exact scalar evaluation on selected v1.54, reusing the frozen warm timing harness."""
import argparse
import json
import queue
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from scripts import daytime_pawn_extrema as trial
from scripts.daytime_common import ROOT, RUN, check_stop, digest, manifest, save
from scripts.daytime_pawn_bitboards_transform import transform

OUT = RUN / 'pawn-bitboards-01'
BASE = RUN / 'pawn-extrema-01/prototype'


def prepare():
    check_stop()
    assert not OUT.exists()
    selected = json.loads((ROOT.parent / 'chessity-agent-version.json').read_text())
    assert selected['version'] == 'v1.54' and digest(ROOT.parent / 'chessity-agent.zip') == selected['sha256']
    trace = json.loads((RUN / 'defence-trace-02/state.json').read_text())
    assert trace['status'] == 'complete' and trace['frozen_candidate']
    prototype = OUT / 'prototype'
    shutil.copytree(BASE, prototype, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    source = transform((BASE / 'engine/compiled_core.py').read_text())
    (prototype / 'engine/compiled_core.py').write_text(source, encoding='utf-8', newline='\n')
    experiment = ROOT / 'experiments/daytime_pawn_bitboards_core.py'
    assert not experiment.exists()
    experiment.write_text(source, encoding='utf-8', newline='\n')
    trace_prep = RUN / 'defence-trace-02/preparation.json'
    earlier = RUN / 'pawn-extrema-01/preparation.json'
    roots = [{k:r[k] for k in ('id','start_fen','history','fen')} for r in json.loads(trace_prep.read_text())['roots']]
    roots += json.loads(earlier.read_text())['roots'][:4]
    assert len(roots) == 12 and len({r['fen'] for r in roots}) == 12
    paths = [Path(__file__), Path(trial.__file__), ROOT / 'scripts/daytime_pawn_bitboards_transform.py',
        ROOT / 'scripts/pawn_mask_transform.py', ROOT / 'scripts/daytime_common.py', experiment,
        ROOT / 'tests/test_daytime_pawn_bitboards.py', ROOT / 'docs/DAYTIME_PAWN_BITBOARDS_20260909.md',
        trace_prep, earlier]
    save(OUT / 'preparation.json', dict(created_utc=datetime.now(timezone.utc).isoformat(),
        candidates={'baseline':str(BASE.relative_to(ROOT)), 'prototype':str(prototype.relative_to(ROOT))},
        candidate_files={'baseline':manifest(BASE), 'prototype':manifest(prototype)}, roots=roots,
        source_sha256={str(p.relative_to(ROOT)):digest(p) for p in paths},
        protocol=dict(fixed_nodes=250000, fixed_seconds_cap=12, clock_seconds=1,
            order=['baseline','prototype','prototype','baseline'], minimum_cpu_ratio=1.05),
        scope='Exact scalar pawn masks rebuilt during existing evaluator scan, no maintained metadata or other prior53 changes.'))
    print('Prepared exact scalar evaluator on v1.54', flush=True)


class Worker(trial.WarmWorker):
    def __init__(self, label):
        self.label = label
        self.log = (OUT / f'{label}.log').open('w', encoding='utf-8')
        self.answers = queue.Queue()
        self.process = subprocess.Popen([sys.executable, '-X', 'utf8', '-m', 'scripts.daytime_pawn_bitboards',
            '--worker', label], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
            text=True, encoding='utf-8', creationflags=subprocess.CREATE_NO_WINDOW)
        def read():
            for line in self.process.stdout:
                self.answers.put(line)
            self.answers.put(None)
        threading.Thread(target=read, daemon=True).start()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--worker', choices=('baseline','prototype'))
    args = parser.parse_args()
    if args.prepare:
        prepare()
    else:
        trial.OUT, trial.BASE, trial.WarmWorker = OUT, BASE, Worker
        trial.worker(args.worker) if args.worker else trial.controller()
