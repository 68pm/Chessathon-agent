"""Cycle20: one bounded aspiration comparison with the selected working startup."""
import json
import os
import statistics
import subprocess
import sys

from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import manifest
from scripts.overnight_capacity import wait_for_capacity
from training.fastchess_data import ROOT
from training.mistake_replay import review_choices


def main():
    out = ROOT / 'runs/improvement-loop-20260907/cycle-20'
    prep = json.loads((out / 'preparation.json').read_text())
    if (out / 'context.json').exists():
        raise ValueError('This comparison is single-use; preserve failures without unchanged retries.')
    base = ROOT / 'candidates/compiled-startup-plain-v1'
    prototype = out / 'prototype'
    roots_path = out / 'roots.jsonl'
    rows = [json.loads(line) for line in roots_path.read_text().splitlines()]
    assert len(rows) == 17 and len({r['id'] for r in rows}) == 17
    assert prep['baseline_files'] == manifest(base) and prep['prototype_files'] == manifest(prototype)
    assert prep['roots_sha256'] == sha256(roots_path)
    for name, digest in prep['source_files'].items():
        assert sha256(ROOT / name) == digest
    state = dict(status='running', source_sha256=sha256(__file__), preparation_sha256=sha256(out / 'preparation.json'),
        stage='position-passes', completed_passes=[])
    save_json(out / 'context.json', state)
    try:
        measurements = {}
        for label, candidate in [('baseline-1', base), ('prototype-1', prototype),
                                 ('prototype-2', prototype), ('baseline-2', base)]:
            wait_for_capacity(out / (label + '-capacity.json'))
            target = out / (label + '.json')
            with (out / (label + '.log')).open('x', encoding='utf-8') as log:
                subprocess.run([sys.executable, '-m', 'scripts.startup_search_probe', '--candidate', str(candidate),
                    '--roots', str(roots_path), '--out', str(target)], cwd=ROOT, stdout=log,
                    stderr=subprocess.STDOUT, check=True, timeout=180,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            report = json.loads(target.read_text())
            assert report['status'] == 'complete' and report['roots_sha256'] == sha256(roots_path)
            assert [r['id'] for r in report['results']] == [r['id'] for r in rows]
            measurements[label] = report['results']
            state['completed_passes'].append(label)
            save_json(out / 'context.json', state)
            print('Completed ' + label, flush=True)
        groups = {name: [r for label, values in measurements.items() if label.startswith(name) for r in values]
                  for name in ['baseline', 'prototype']}
        depths = {name: statistics.mean(r['depth'] for r in values) for name, values in groups.items()}
        repeats = {name: sum(r['repeats_large_error'] for r in values) for name, values in groups.items()}
        gain = depths['prototype'] - depths['baseline']
        cheap = (gain >= .25 or repeats['prototype'] < repeats['baseline']) and repeats['prototype'] <= repeats['baseline']
        teacher = None
        passed = False
        if cheap:
            state['stage'] = 'bounded-teacher-review'
            save_json(out / 'context.json', state)
            wait_for_capacity(out / 'teacher-capacity.json')
            reviews = {}
            for label, choices in measurements.items():
                reviews[label] = review_choices([dict(root=r) for r in rows], choices, out / 'choice-cache.jsonl')
                save_json(out / (label + '-review.json'), reviews[label])
            means = {name: [statistics.mean(reviews[name + '-' + str(i)]['mean_regret'][j] for i in [1, 2])
                     for j in [0, 1]] for name in ['baseline', 'prototype']}
            errors, mates = [], []
            for i in [1, 2]:
                for a, b in zip(reviews[f'baseline-{i}']['records'], reviews[f'prototype-{i}']['records'], strict=True):
                    assert a['id'] == b['id']
                    if max(a['regret']) < 200 and min(b['regret']) >= 200:
                        errors.append(dict(pass_number=i, id=a['id']))
                    if b['mate_loss'] and not a['mate_loss']:
                        mates.append(dict(pass_number=i, id=a['id']))
            no_regression = all(b <= a for a, b in zip(means['baseline'], means['prototype'], strict=True))
            improves = all(b < a for a, b in zip(means['baseline'], means['prototype'], strict=True)) or gain >= .25
            passed = not errors and not mates and no_regression and improves
            teacher = dict(mean_regret=means, new_errors=errors, new_mates=mates,
                newly_requested_nodes=sum(r['new_teacher_nodes'] for r in reviews.values()))
        assert prep['baseline_files'] == manifest(base) and prep['prototype_files'] == manifest(prototype)
        for name, digest in prep['source_files'].items():
            assert sha256(ROOT / name) == digest
        result = dict(status='complete', passed=passed, automatic_promotion=False, cheap_pass=cheap,
            mean_depth=depths, depth_gain=gain, error_repeats=repeats, teacher_review=teacher,
            scope='Exposed development positions. Pass permits read-only validation and two practical games only; no automatic Elo claim.')
        save_json(out / 'gate.json', result)
        state.update(status='complete', passed=passed, stage='awaiting_critique')
        print(json.dumps(result), flush=True)
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(out / 'context.json', state)


if __name__ == '__main__':
    main()
