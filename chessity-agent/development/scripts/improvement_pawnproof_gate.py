"""Fixed-work parity and two alternating timing passes for the legal-pawn proof."""

import json
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import manifest
from training.fastchess_data import ROOT


def main():
    out = ROOT / 'runs/improvement-loop-20260907/cycle-13'
    base = ROOT / 'candidates/compiled-qsearch-endgames-v1'
    prototype = out / 'prototype'
    source = ROOT / 'runs/improvement-loop-20260907/cycle-10/audited-roots.jsonl'
    tests = out / 'pawnproof-tests.xml'
    suite = ET.parse(tests).getroot().find('testsuite')
    assert int(suite.attrib['tests']) == 9
    assert all(int(suite.attrib[k]) == 0 for k in ('errors', 'failures', 'skipped'))
    if prototype.exists() or (out / 'gate-context.json').exists():
        raise ValueError('Preserve every measured pilot; no timing retries.')
    shutil.copytree(base, prototype, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(ROOT / 'experiments/pawnproof_core.py', prototype / 'engine/compiled_core.py')
    before, after = manifest(base), manifest(prototype)
    assert before.keys() == after.keys()
    assert [k for k in before if before[k] != after[k]] == ['engine/compiled_core.py']
    rows = [json.loads(line) for line in source.read_text().splitlines()]
    assert len(rows) == 11
    shutil.copy2(ROOT / 'docs/IMPROVEMENT_CYCLE_13.md', out / 'predeclaration.md')
    context = dict(status='running', roots_sha256=sha256(source), tests_sha256=sha256(tests),
        gate_code_sha256=sha256(__file__), predeclaration_sha256=sha256(out / 'predeclaration.md'),
        baseline_files=before, prototype_files=after, roots=11, nodes_per_root=250000,
        scope='Fixed-work diagnostic timing, not rating evidence.')
    save_json(out / 'gate-context.json', context)
    try:
        results = {}
        for label, path in [('baseline-1', base), ('prototype-1', prototype),
                            ('prototype-2', prototype), ('baseline-2', base)]:
            if any((ROOT / flag).exists() for flag in ['STOP_TRAINING', 'STOP_BENCHMARK']):
                raise InterruptedError('User stop flag')
            target = out / f'{label}.json'
            with (out / f'{label}.log').open('w', encoding='utf-8') as log:
                subprocess.run([sys.executable, '-m', 'scripts.improvement_probe',
                    '--candidate', str(path), '--audit', str(source), '--out', str(target),
                    '--seconds', '20', '--nodes', '250000'], cwd=ROOT, stdout=log,
                    stderr=subprocess.STDOUT, check=True, timeout=300)
            report = json.loads(target.read_text())
            assert report['audit_sha256'] == sha256(source)
            results[label] = report['results']
            assert [r['id'] for r in results[label]] == [r['id'] for r in rows]
            print('Completed ' + label, flush=True)
        fields = ['id', 'uci', 'score', 'depth', 'nodes']
        reference = [{k: r[k] for k in fields} for r in results['baseline-1']]
        parity = all([{k: r[k] for k in fields} for r in values] == reference
                     for values in results.values())
        seconds = {label: sum(r['seconds'] for r in values) for label, values in results.items()}
        speedup = sum(v for k, v in seconds.items() if k.startswith('baseline')) / sum(
            v for k, v in seconds.items() if k.startswith('prototype'))
        assert manifest(base) == before and manifest(prototype) == after
        report = dict(status='complete', passed=parity and speedup >= 1.10,
            exact_fixed_work_parity=parity, seconds=seconds, speedup=speedup,
            scope=context['scope'])
        save_json(out / 'gate.json', report)
        context.update(status='complete', passed=report['passed'])
        print(json.dumps(report), flush=True)
    except BaseException as error:
        context.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(out / 'gate-context.json', context)


if __name__ == '__main__':
    main()
