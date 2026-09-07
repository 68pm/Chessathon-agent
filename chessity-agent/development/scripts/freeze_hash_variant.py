"""Freeze the isolated hash variant only after its declared pilot has passed."""

import json
import shutil
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from scripts.build_submission import build
from scripts.improvement_hash_gate import digest, files, save
from training.fastchess_data import ROOT


def main():
    run = ROOT / 'runs/improvement-loop-20260907/cycle-08'
    context = json.loads((run / 'hash-gate-context.json').read_text(encoding='utf-8'))
    gate = json.loads((run / 'hash-gate.json').read_text(encoding='utf-8'))
    tests = ET.parse(run / 'hash-tests.xml').getroot().findall('testsuite')
    assert tests and sum(int(s.get('tests', '0')) for s in tests) == 6
    assert all(int(s.get(k, '0')) == 0 for s in tests for k in ['errors', 'failures', 'skipped'])
    assert context['status'] == 'complete' and context['passed'] and gate['passed']
    assert all(gate['checks'].values())
    for name, expected in gate['source_sha256'].items():
        assert digest(run / f'{name}.json') == expected
    source = run / 'prototype'
    base = ROOT / 'candidates/compiled-qsearch-endgames-v1'
    assert files(source) == context['prototype_files'] and files(base) == context['baseline_files']
    target = ROOT / 'candidates/compiled-incremental-hash-v1'
    assert not target.exists() and not target.with_suffix('.zip').exists()
    shutil.copytree(source, target, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    assert files(target) == context['prototype_files']
    manifest = build(target, target.with_suffix('.zip'))
    record = dict(status='frozen_pending_readonly', candidate=str(target.relative_to(ROOT)),
                  created_utc=datetime.now(timezone.utc).isoformat(), manifest=manifest,
                  gate_sha256=digest(run / 'hash-gate.json'), tests_sha256=digest(run / 'hash-tests.xml'),
                  changed_runtime_files=['engine/compiled_core.py'],
                  scope='Experimental. Selected v1.41 is unchanged; no strength promotion.')
    save(run / 'freeze.json', record)
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
