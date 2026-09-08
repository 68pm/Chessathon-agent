"""Single bounded two-check-extension pilot, preserving all outcomes."""
import json
import os
import statistics
import subprocess
import sys
import xml.etree.ElementTree as ET

from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import manifest
from scripts.overnight_capacity import wait_for_capacity
from training.fastchess_data import ROOT
from training.mistake_replay import review_choices


def child(arguments, log, timeout=300):
    """A Windows venv launcher may have a child interpreter; bound the owned tree."""
    with log.open('x', encoding='utf-8') as stream:
        with subprocess.Popen([sys.executable, *arguments], cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0) as process:
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                if process.poll() is None:
                    if os.name == 'nt':
                        subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'],
                            stdout=stream, stderr=subprocess.STDOUT, check=True,
                            creationflags=subprocess.CREATE_NO_WINDOW)
                    else:
                        process.kill()
                process.wait(timeout=15)
                raise
            if code:
                raise subprocess.CalledProcessError(code, arguments)


def main():
    out = ROOT / 'runs/improvement-loop-20260907/cycle-23'
    if (out / 'context.json').exists():
        raise ValueError('No unchanged pilot retries')
    prep = json.loads((out / 'preparation.json').read_text())
    base = ROOT / 'candidates/compiled-startup-plain-v1'
    prototype = out / 'prototype'
    assert manifest(base) == prep['baseline_files'] and manifest(prototype) == prep['prototype_files']
    for name, digest in prep['source_files'].items():
        assert sha256(ROOT / name) == digest
    state = dict(status='running', stage='correctness', preparation_sha256=sha256(out / 'preparation.json'),
        source_sha256=sha256(__file__), completed_probes=[])
    save_json(out / 'context.json', state)
    try:
        wait_for_capacity(out / 'tests-capacity.json')
        xml = out / 'tests.xml'
        child(['-m', 'pytest', 'tests/test_check_extensions.py', '-q', '--junitxml', str(xml)], out / 'tests.log')
        suite = ET.parse(xml).getroot().find('testsuite')
        assert int(suite.attrib['tests']) == 10
        assert all(int(suite.attrib[k]) == 0 for k in ['errors', 'failures', 'skipped'])
        state['stage'] = 'position-probes'
        save_json(out / 'context.json', state)
        roots = out / 'roots.jsonl'
        assert sha256(roots) == prep['roots_sha256']
        rows = [json.loads(line) for line in roots.read_text().splitlines()]
        extra = [r for r in rows if r['id'].startswith('startup19-')]
        assert len(rows) == 17 and len(extra) == 3
        ordered = rows + extra
        measurements = {}
        for label, candidate in [('baseline', base), ('prototype', prototype)]:
            wait_for_capacity(out / (label + '-capacity.json'))
            target = out / (label + '.json')
            child(['-m', 'scripts.quiet_check_probe', '--candidate', str(candidate), '--roots', str(roots),
                '--out', str(target)], out / (label + '.log'))
            report = json.loads(target.read_text())
            assert report['status'] == 'complete' and report['roots_sha256'] == sha256(roots)
            assert [(r['id'], r['mode']) for r in report['results']] == (
                [(r['id'], 'clock') for r in rows] + [(r['id'], 'nodes') for r in extra])
            measurements[label] = report['results']
            state['completed_probes'].append(label)
            save_json(out / 'context.json', state)
            print('Completed ' + label, flush=True)
        repeats = {label: sum(r['repeats_large_error'] for r in values[:17]) for label, values in measurements.items()}
        king_id = 'startup19-game-001-ply-062'
        king_changed = any(r['id'] == king_id and r['uci'] != 'g1f1' for r in measurements['prototype'])
        cheap = repeats['prototype'] < repeats['baseline'] and king_changed
        passed, teacher = False, None
        if cheap:
            state['stage'] = 'bounded-teacher-review'
            save_json(out / 'context.json', state)
            wait_for_capacity(out / 'teacher-capacity.json')
            reviews = {}
            for label, choices in measurements.items():
                reviews[label] = review_choices([dict(root=r) for r in ordered], choices, out / 'choice-cache.jsonl')
                save_json(out / (label + '-review.json'), reviews[label])
            means = {label: [statistics.mean(r['regret'][i] for r in review['records'][:17])
                for i in [0, 1]] for label, review in reviews.items()}
            errors, mates = [], []
            for index, (a, b) in enumerate(zip(reviews['baseline']['records'], reviews['prototype']['records'], strict=True)):
                assert a['id'] == b['id']
                if max(a['regret']) < 200 and min(b['regret']) >= 200:
                    errors.append(dict(index=index, id=a['id']))
                if b['mate_loss'] and not a['mate_loss']:
                    mates.append(dict(index=index, id=a['id']))
            repaired_king = any(r['id'] == king_id and max(r['regret']) <= 50 for r in reviews['prototype']['records'])
            passed = (not errors and not mates and repaired_king
                and all(b < a for a, b in zip(means['baseline'], means['prototype'], strict=True)))
            teacher = dict(clock_mean_regret=means, new_errors=errors, new_mates=mates, repaired_king=repaired_king,
                newly_requested_nodes=sum(v['new_teacher_nodes'] for v in reviews.values()))
        assert manifest(base) == prep['baseline_files'] and manifest(prototype) == prep['prototype_files']
        for name, digest in prep['source_files'].items():
            assert sha256(ROOT / name) == digest
        result = dict(status='complete', passed=passed, automatic_promotion=False, cheap_pass=cheap,
            clock_error_repeats=repeats, king_choice_changed=king_changed, teacher_review=teacher,
            scope='Exposed targeted pilot; pass permits read-only checks and two practical games, not a rating claim.')
        save_json(out / 'gate.json', result)
        state.update(status='complete', stage='awaiting_critique', passed=passed)
        print(json.dumps(result), flush=True)
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(out / 'context.json', state)


if __name__ == '__main__':
    main()
