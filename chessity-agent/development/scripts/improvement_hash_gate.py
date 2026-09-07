"""One bounded, predeclared differential speed pilot on already audited roots."""

import hashlib
import json
import shutil
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from training.fastchess_data import ROOT


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def files(path):
    return {p.relative_to(path).as_posix(): digest(p) for p in sorted(path.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8', newline='\n')


def main():
    out = ROOT / 'runs/improvement-loop-20260907/cycle-08'
    base = ROOT / 'candidates/compiled-qsearch-endgames-v1'
    prototype = out / 'prototype'
    audit = out / 'audited-roots.jsonl'
    if prototype.exists() or audit.exists():
        raise ValueError('Pilot is single-use. Preserve existing measurements and failures.')
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(base, prototype, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(ROOT / 'experiments/hash_core.py', prototype / 'engine/compiled_core.py')
    original, changed = files(base), files(prototype)
    assert original.keys() == changed.keys()
    assert [p for p in original if original[p] != changed[p]] == ['engine/compiled_core.py']
    sources = [('v1.41-confirmation', 'confirmation-01'), ('v1.47-development', 'cycle-07')]
    rows, known, source_records = [], {}, []
    for namespace, directory in sources:
        source = ROOT / 'runs/improvement-loop-20260907' / directory / 'rated-error-audit/positions.jsonl'
        source_records.append(dict(path=str(source.relative_to(ROOT)), sha256=digest(source)))
        for row in map(json.loads, source.read_text(encoding='utf-8').splitlines()):
            if row['label'] != 'verified_200cp_error':
                continue
            key = (row['start_fen'], tuple(row['history']))
            reference = dict(source=namespace, original_id=row['id'], original_played=row['played'])
            if key in known:
                rows[known[key]]['pilot_sources'].append(reference)
                continue
            known[key] = len(rows)
            row['id'] = namespace + ':' + row['id']
            row['pilot_sources'] = [reference]
            rows.append(row)
    assert rows
    audit.write_text(''.join(json.dumps(row) + '\n' for row in rows), encoding='utf-8', newline='\n')
    context = dict(status='running', started_utc=datetime.now(timezone.utc).isoformat(),
                   predeclaration_sha256=digest(ROOT / 'docs/IMPROVEMENT_CYCLE_08.md'),
                   gate_code_sha256=digest(Path(__file__)), sources=source_records,
                   baseline_files=original, prototype_files=changed,
                   roots_sha256=digest(audit), roots=len(rows),
                   scope='Exposed-root correctness and efficiency gate, not independent strength evidence.')
    save(out / 'hash-gate-context.json', context)
    try:
        for mode, seconds, nodes in [('fixed', 20, 500000), ('clock', 1, None)]:
            for label, candidate in [('baseline', base), ('prototype', prototype)]:
                if any((ROOT / flag).exists() for flag in ['STOP_TRAINING', 'STOP_BENCHMARK']):
                    raise RuntimeError('Stop flag requested.')
                result = out / f'{label}-{mode}.json'
                assert not result.exists()
                command = [sys.executable, '-m', 'scripts.improvement_probe', '--candidate', str(candidate),
                           '--audit', str(audit), '--out', str(result), '--seconds', str(seconds)]
                if nodes is not None:
                    command += ['--nodes', str(nodes)]
                with (out / f'{label}-{mode}.log').open('w', encoding='utf-8') as log:
                    subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                   check=True, timeout=120 + seconds * len(rows))
                print(f'Completed {label} {mode}', flush=True)
        measurements = {name: json.loads((out / f'{name}.json').read_text(encoding='utf-8'))
                        for name in ['baseline-fixed', 'prototype-fixed', 'baseline-clock', 'prototype-clock']}
        assert all(report['audit_sha256'] == digest(audit) for report in measurements.values())
        fixed = []
        for a, b in zip(measurements['baseline-fixed']['results'], measurements['prototype-fixed']['results'], strict=True):
            parity = all(a[k] == b[k] for k in ['id', 'uci', 'score', 'depth', 'nodes', 'fen'])
            budget = a['nodes'] >= 500000 and b['nodes'] >= 500000
            early = parity and (abs(a['score']) >= 29000 or a['depth'] == 64)
            fixed.append(dict(id=a['id'], exact_parity=parity, node_budget_or_same_early_stop=budget or early,
                              elapsed_ratio=a['seconds'] / b['seconds'], baseline=a, prototype=b))
        a, b = [measurements[name]['results'] for name in ['baseline-clock', 'prototype-clock']]
        assert [r['id'] for r in a] == [r['id'] for r in b]
        depths = [statistics.mean(r['depth'] for r in results) for results in [a, b]]
        errors = [sum(r['repeats_large_error'] for r in results) for results in [a, b]]
        ratio = statistics.median(r['elapsed_ratio'] for r in fixed)
        checks = dict(fixed_work_exact_parity=all(r['exact_parity'] for r in fixed),
                      node_budget_or_same_early_stop=all(r['node_budget_or_same_early_stop'] for r in fixed),
                      median_speedup_at_least_1_10=ratio >= 1.10,
                      clock_mean_depth_not_lower=depths[1] >= depths[0],
                      clock_repeated_errors_not_more=errors[1] <= errors[0],
                      frozen_inputs=files(base) == original and files(prototype) == changed)
        gate = dict(passed=all(checks.values()), checks=checks, roots=len(rows),
                    median_equal_work_speedup=ratio, clock_mean_depth_baseline_prototype=depths,
                    clock_error_repeats_baseline_prototype=errors, fixed_rows=fixed,
                    source_sha256={name: digest(out / f'{name}.json') for name in measurements},
                    scope=context['scope'])
        save(out / 'hash-gate.json', gate)
        context.update(status='complete', passed=gate['passed'])
        print(json.dumps({k: v for k, v in gate.items() if k != 'fixed_rows'}), flush=True)
    except BaseException as error:
        context.update(status='failed', error=repr(error))
        raise
    finally:
        context['completed_utc'] = datetime.now(timezone.utc).isoformat()
        save(out / 'hash-gate-context.json', context)


if __name__ == '__main__':
    main()
