"""One short, predeclared diagnostic gate before spending time on match games."""

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
    out = ROOT / 'runs/improvement-loop-20260907/cycle-10'
    base = ROOT / 'candidates/compiled-qsearch-endgames-v1'
    prototype = out / 'prototype'
    sources = [ROOT / 'runs/improvement-loop-20260907/confirmation-01/rated-error-audit/positions.jsonl',
               ROOT / 'runs/improvement-loop-20260907/competition-20260907/targets.jsonl']
    tests = out / 'null-tests.xml'
    suite = ET.parse(tests).getroot().find('testsuite')
    assert int(suite.attrib['tests']) == 11
    assert all(int(suite.attrib[k]) == 0 for k in ('errors', 'failures', 'skipped'))
    if prototype.exists() or (out / 'gate-context.json').exists():
        raise ValueError('Preserve this single-use pilot, including failed measurements.')
    shutil.copytree(base, prototype, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    shutil.copy2(ROOT / 'experiments/nullmove_core.py', prototype / 'engine/compiled_core.py')
    before, after = manifest(base), manifest(prototype)
    assert before.keys() == after.keys()
    assert [k for k in before if before[k] != after[k]] == ['engine/compiled_core.py']
    rows = [r for source in sources for r in map(json.loads, source.read_text().splitlines())
            if r['label'] == 'verified_200cp_error']
    assert len(rows) == 11 and len({r['id'] for r in rows}) == 11
    audit = out / 'audited-roots.jsonl'
    audit.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8', newline='\n')
    shutil.copy2(ROOT / 'docs/IMPROVEMENT_CYCLE_10.md', out / 'predeclaration.md')
    context = dict(status='running', sources={str(p): sha256(p) for p in sources},
        roots_sha256=sha256(audit), tests_sha256=sha256(tests), gate_code_sha256=sha256(__file__),
        predeclaration_sha256=sha256(out / 'predeclaration.md'),
        baseline_files=before, prototype_files=after, teacher_sha256=sha256(SF),
        roots=11, scope='Exposed v1.41 errors; mechanism development, not strength evidence.')
    save_json(out / 'gate-context.json', context)

    def stop_check():
        if any((ROOT / flag).exists() for flag in ['STOP_TRAINING', 'STOP_BENCHMARK']):
            raise InterruptedError('User stop flag')

    try:
        measurements = {}
        for name, path in [('baseline', base), ('prototype', prototype)]:
            stop_check()
            target = out / f'{name}-clock.json'
            with (out / f'{name}-clock.log').open('w', encoding='utf-8') as log:
                subprocess.run([sys.executable, '-m', 'scripts.improvement_probe',
                    '--candidate', str(path), '--audit', str(audit), '--out', str(target),
                    '--seconds', '1'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                    check=True, timeout=180)
            report = json.loads(target.read_text())
            assert report['audit_sha256'] == sha256(audit)
            assert [r['id'] for r in report['results']] == [r['id'] for r in rows]
            measurements[name] = report['results']
            print('Completed ' + name, flush=True)
        summary = {k: dict(error_repeats=sum(r['repeats_large_error'] for r in values),
            recent_error_repeats=sum(r['repeats_large_error'] for r in values[-3:]),
            teacher_agreement=sum(r['agrees_with_deep_teacher'] for r in values),
            mean_depth=statistics.mean(r['depth'] for r in values),
            nodes=sum(r['nodes'] for r in values), seconds=sum(r['seconds'] for r in values))
            for k, values in measurements.items()}
        cheap_pass = (summary['prototype']['error_repeats'] < summary['baseline']['error_repeats']
                      and summary['prototype']['recent_error_repeats'] <= summary['baseline']['recent_error_repeats'])
        report = dict(status='complete', passed=False, summary=summary,
                      cheap_pass=cheap_pass, teacher_review=None, scope=context['scope'])
        if cheap_pass:
            teacher = Verifier(SF)
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
                                    value = evaluate(teacher.engine, board, budget, move)
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
                teacher.close()
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
