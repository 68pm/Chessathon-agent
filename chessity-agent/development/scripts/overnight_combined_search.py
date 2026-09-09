"""Combine independent exact attack and quiet-check work reductions on repaired53."""

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

from scripts import overnight_check_prefilter as trial
from scripts.overnight_bitsets_fixed import changed_source as bitsets
from scripts.overnight_geometry_trial import ROOT, digest, manifest, save

OUT = ROOT / 'runs/overnight-20260909/combined-search-01'
BASE = ROOT / 'runs/overnight-20260909/coalesced-search-01/prototype'


def changed_source(original):
    return trial.changed_source(bitsets(original))


def prepare():
    assert not OUT.exists(), 'Preserve completed and partial preparations.'
    OUT.mkdir()
    prototype = OUT / 'prototype'
    shutil.copytree(BASE, prototype, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    source = changed_source((BASE / 'engine/compiled_core.py').read_text(encoding='utf-8'))
    (prototype / 'engine/compiled_core.py').write_text(source, encoding='utf-8', newline='\n')
    helper = ROOT / 'experiments/overnight_bitsets_attacks_fixed.py'
    shutil.copy2(helper, prototype / 'engine/overnight_bitsets_attacks_fixed.py')
    driver_path = prototype / 'engine/compiled_driver.py'
    driver = driver_path.read_text(encoding='utf-8')
    old = 'pieces = np.zeros(128, dtype=np.int64)'
    assert driver.count(old) == 1
    driver = driver.replace(old, 'pieces = np.zeros(142, dtype=np.int64)')
    old = '    rights = (int(board.has_kingside_castling_rights(True))'
    assert driver.count(old) == 1
    driver = driver.replace(old, '    core.rebuild_metadata(pieces)\n' + old)
    driver_path.write_text(driver, encoding='utf-8', newline='\n')
    experiment = ROOT / 'experiments/overnight_combined_search_core.py'
    assert not experiment.exists()
    experiment.write_text(source, encoding='utf-8', newline='\n')
    earlier = OUT.parent / 'check-prefilter-01/preparation.json'
    roots = json.loads(earlier.read_text(encoding='utf-8'))['roots']
    assert len(roots) == 22
    paths = [Path(__file__), Path(trial.__file__), ROOT / 'scripts/overnight_bitsets_fixed.py',
        ROOT / 'scripts/overnight_classical_kernel.py', ROOT / 'scripts/overnight_hash_scout_fixed.py',
        ROOT / 'scripts/overnight_geometry_trial.py', ROOT / 'tests/test_overnight_combined_search.py',
        ROOT / 'tests/test_overnight_bitsets_fixed.py', ROOT / 'tests/test_overnight_check_prefilter.py',
        ROOT / 'docs/OVERNIGHT_COMBINED_SEARCH_PLAN_20260909.md', helper, experiment, earlier]
    save(OUT / 'preparation.json', dict(created_utc=datetime.now(timezone.utc).isoformat(),
        candidates={'baseline': str(BASE.relative_to(ROOT)), 'prototype': str(prototype.relative_to(ROOT))},
        candidate_files={'baseline': manifest(BASE), 'prototype': manifest(prototype)}, roots=roots,
        source_sha256={str(p.relative_to(ROOT)): digest(p) for p in paths},
        fixed_nodes=250000, per_root_order='ABBA', runtime_speedup_gate=1.10, startup_gate_seconds=90,
        scope='New combined mechanism. Matched compiler-repaired control, not exact v1.53 ZIP. Earlier failed trials stay failed.'))


class WarmWorker(trial.WarmWorker):
    def __init__(self, label):
        self.label = label
        self.log = (OUT / f'{label}.log').open('w', encoding='utf-8')
        self.answers = queue.Queue()
        self.process = subprocess.Popen([sys.executable, '-X', 'utf8', '-m',
            'scripts.overnight_combined_search', '--worker', label], cwd=ROOT,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
            text=True, encoding='utf-8',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)

        def read():
            for line in self.process.stdout:
                self.answers.put(line)
            self.answers.put(None)
        threading.Thread(target=read, daemon=True).start()


def execute(label=None):
    original = trial.OUT, trial.BASE, trial.WarmWorker
    try:
        trial.OUT, trial.BASE, trial.WarmWorker = OUT, BASE, WarmWorker
        if label:
            trial.worker(label)
        else:
            trial.controller()
    finally:
        trial.OUT, trial.BASE, trial.WarmWorker = original


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--worker', choices=('baseline', 'prototype'))
    args = parser.parse_args()
    if args.prepare:
        prepare()
    else:
        execute(args.worker)
