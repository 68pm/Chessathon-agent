"""Reuse exact old fixed-node work; verify one targeted evaluation change."""

import json
import shutil
import statistics
import subprocess
import sys
import xml.etree.ElementTree as ET

import chess

from scripts.alien_rating_ladder import save_json, sha256
from scripts.improvement_audit import evaluate
from scripts.magnus_benchmark import SF, manifest
from training.counterfactual_value import restore_root
from training.fastchess_data import ROOT
from training.puzzle_verifier import Verifier


def main():
    run = ROOT / 'runs/improvement-loop-20260907'
    out = run / 'cycle-15'
    base = ROOT / 'candidates/compiled-pawn-proof-v1'
    prototype = out / 'prototype'
    old_roots = run / 'cycle-10/audited-roots.jsonl'
    new_roots = run / 'cycle-13/pair-audit/positions.jsonl'
    cached_path = run / 'cycle-13/prototype-1.json'
    cached = json.loads(cached_path.read_text())
    tests = out / 'queen-pawn-tests.xml'
    suite = ET.parse(tests).getroot().find('testsuite')
    assert int(suite.attrib['tests']) == 6
    assert all(int(suite.attrib[k]) == 0 for k in ('errors', 'failures', 'skipped'))
    assert cached['audit_sha256'] == sha256(old_roots) and cached['requested_nodes'] == 250000
    assert manifest(base) == json.loads((run / 'cycle-13/gate-context.json').read_text())['prototype_files']
    if prototype.exists() or (out / 'gate-context.json').exists():
        raise ValueError('This fixed pilot is single-use.')
    shutil.copytree(base, prototype, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(ROOT / 'experiments/queen_pawn_core.py', prototype / 'engine/compiled_core.py')
    before, after = manifest(base), manifest(prototype)
    assert [k for k in before if before[k] != after[k]] == ['engine/compiled_core.py']
    old = [json.loads(line) for line in old_roots.read_text().splitlines()]
    new = [r for r in map(json.loads, new_roots.read_text().splitlines()) if r['label'] == 'verified_200cp_error']
    rows = old + new
    assert len(old) == 11 and len(new) == 3 and len({r['id'] for r in rows}) == 14
    assert [r['id'] for r in old] == [r['id'] for r in cached['results']]
    all_path, new_path = out / 'all-roots.jsonl', out / 'new-roots.jsonl'
    for p, values in [(all_path, rows), (new_path, new)]:
        p.write_text(''.join(json.dumps(r) + '\n' for r in values), encoding='utf-8', newline='\n')
    shutil.copy2(ROOT / 'docs/IMPROVEMENT_CYCLE_15.md', out / 'predeclaration.md')
    context = dict(status='running', roots_sha256=sha256(all_path),
        baseline_cache_sha256=sha256(cached_path), tests_sha256=sha256(tests),
        gate_code_sha256=sha256(__file__), predeclaration_sha256=sha256(out / 'predeclaration.md'),
        baseline_files=before, prototype_files=after, teacher_sha256=sha256(SF))
    save_json(out / 'gate-context.json', context)

    def stop_check():
        if any((ROOT / flag).exists() for flag in ['STOP_TRAINING', 'STOP_BENCHMARK']):
            raise InterruptedError('User stop flag')

    try:
        measurements = {}
        for name, path, audit in [('baseline', base, new_path), ('prototype', prototype, all_path)]:
            stop_check()
            target = out / f'{name}-probe.json'
            with (out / f'{name}-probe.log').open('w', encoding='utf-8') as log:
                subprocess.run([sys.executable, '-m', 'scripts.improvement_probe', '--candidate', str(path),
                    '--audit', str(audit), '--out', str(target), '--seconds', '20', '--nodes', '250000'],
                    cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=300)
            result = json.loads(target.read_text())
            assert result['audit_sha256'] == sha256(audit)
            measurements[name] = (cached['results'] if name == 'baseline' else []) + result['results']
            assert [r['id'] for r in measurements[name]] == [r['id'] for r in rows]
            print('Completed ' + name, flush=True)
        repeats = {name: sum(r['repeats_large_error'] for r in values)
                   for name, values in measurements.items()}
        motivating = next(r for r in measurements['prototype'] if r['id'] == 'game-002-ply-101')
        cheap = repeats['prototype'] < repeats['baseline'] and not motivating['repeats_large_error']
        report = dict(status='complete', passed=False, error_repeats=repeats, cheap_pass=cheap,
                      motivating_choice=motivating, teacher_review=None)
        if cheap:
            verifier = Verifier(SF)
            records, cache, requested = [], {}, 0
            try:
                for index, row in enumerate(rows):
                    board = restore_root(row)
                    record = dict(id=row['id'], variants={})
                    for name in ['baseline', 'prototype']:
                        uci = measurements[name][index]['uci']
                        move = chess.Move.from_uci(uci)
                        assert move in board.legal_moves
                        values, regrets = [], []
                        for j, budget in enumerate([80000, 320000]):
                            original = row['verification'][j]
                            key = (row['id'], uci, budget)
                            if key not in cache:
                                if uci == row['played']:
                                    value = original['played']
                                elif uci == original['best']['pv'][0]:
                                    value = original['best']
                                else:
                                    stop_check()
                                    value = evaluate(verifier.engine, board, budget, move)
                                    requested += budget
                                cache[key] = value
                            value = cache[key]
                            values.append(value)
                            regrets.append(min(1000, max(0, original['best']['cp'] - value['cp']))
                                if value['cp'] is not None else 1000 if value['mate'] < 0 else 0)
                        record['variants'][name] = dict(uci=uci, analysis=values, capped_regret=regrets,
                            mate_loss=all(v['mate'] is not None and v['mate'] < 0 for v in values))
                    records.append(record)
            finally:
                verifier.close()
            means = {name: [statistics.mean(r['variants'][name]['capped_regret'][j] for r in records)
                           for j in range(2)] for name in ['baseline', 'prototype']}
            losses = {name: sum(r['variants'][name]['mate_loss'] for r in records)
                      for name in ['baseline', 'prototype']}
            report['passed'] = (losses['prototype'] <= losses['baseline'] and
                all(a < b for a, b in zip(means['prototype'], means['baseline'], strict=True)))
            report['teacher_review'] = dict(records=records, mean_capped_regret=means,
                mate_losses=losses, newly_requested_nodes=requested)
        assert manifest(base) == before and manifest(prototype) == after
        save_json(out / 'gate.json', report)
        context.update(status='complete', passed=report['passed'])
        print(json.dumps({k: v for k, v in report.items() if k != 'teacher_review'}), flush=True)
    except BaseException as error:
        context.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(out / 'gate-context.json', context)


if __name__ == '__main__':
    main()
