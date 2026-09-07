"""A single bounded cycle17 clock/teacher diagnostic after correctness passes."""
import json
import os
import shutil
import statistics
import subprocess
import sys
import xml.etree.ElementTree as ET

from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import manifest
from scripts.overnight_resources import memory, wait_for_memory
from training.fastchess_data import ROOT
from training.mistake_replay import review_choices


def main():
    run = ROOT / 'runs/improvement-loop-20260907'
    out = run / 'cycle-17'
    base, prototype = ROOT / 'candidates/compiled-qsearch-endgames-v1', out / 'prototype'
    roots_path = run / 'cycle-15/all-roots.jsonl'
    rows = [json.loads(line) for line in roots_path.read_text().splitlines()]
    assert len(rows) == 14 and len({r['id'] for r in rows}) == 14
    assert all(r['label'] == 'verified_200cp_error' for r in rows)
    prerequisite = run / 'overnight-serial-controller/controller.json'
    assert json.loads(prerequisite.read_text())['status'] == 'complete'
    tests = out / 'aspiration-tests.xml'
    suite = ET.parse(tests).getroot().find('testsuite')
    assert int(suite.attrib['tests']) == 9
    assert all(int(suite.attrib[k]) == 0 for k in ['errors','failures','skipped'])
    if prototype.exists() or (out / 'context.json').exists():
        raise ValueError('Preserve earlier measurements; no unchanged timing retries.')
    shutil.copytree(base,prototype,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    shutil.copy2(ROOT / 'experiments/aspiration_core.py',prototype / 'engine/compiled_core.py')
    driver = (ROOT / 'experiments/aspiration_driver.py').read_text().replace(
        'from . import aspiration_core as core','from . import compiled_core as core')
    (prototype / 'engine/compiled_driver.py').write_text(driver,encoding='utf-8',newline='\n')
    before, after = manifest(base),manifest(prototype)
    assert before.keys() == after.keys()
    assert {k for k in before if before[k] != after[k]} == {'engine/compiled_core.py','engine/compiled_driver.py'}
    shutil.copy2(ROOT / 'docs/IMPROVEMENT_CYCLE_17.md',out / 'predeclaration.md')
    context = dict(status='running',source_sha256=sha256(__file__),roots_sha256=sha256(roots_path),
        tests_sha256=sha256(tests),predeclaration_sha256=sha256(out / 'predeclaration.md'),
        prerequisite_sha256=sha256(prerequisite),baseline_files=before,prototype_files=after,
        start_memory=memory())
    save_json(out / 'context.json',context)
    try:
        measurements = {}
        for label, candidate in [('baseline-1',base),('prototype-1',prototype),('prototype-2',prototype),('baseline-2',base)]:
            wait_for_memory(out / 'resources.json')
            target = out / (label+'.json')
            with (out / (label+'.log')).open('w',encoding='utf-8') as log:
                subprocess.run([sys.executable,'-m','scripts.improvement_probe','--candidate',str(candidate),
                    '--audit',str(roots_path),'--out',str(target),'--seconds','1'],cwd=ROOT,stdout=log,
                    stderr=subprocess.STDOUT,check=True,timeout=300,
                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            report = json.loads(target.read_text())
            assert report['audit_sha256'] == sha256(roots_path)
            measurements[label] = report['results']
            assert [r['id'] for r in report['results']] == [r['id'] for r in rows]
            print('Completed '+label,flush=True)
        groups = {name:[r for label, values in measurements.items() if label.startswith(name) for r in values]
            for name in ['baseline','prototype']}
        depth = {name:statistics.mean(r['depth'] for r in values) for name,values in groups.items()}
        repeats = {name:sum(r['repeats_large_error'] for r in values) for name,values in groups.items()}
        depth_gain = depth['prototype'] - depth['baseline']
        cheap = (depth_gain >= .25 or repeats['prototype'] < repeats['baseline']) and repeats['prototype'] <= repeats['baseline']
        reviews = {}
        passed = False
        if cheap:
            for label, choices in measurements.items():
                reviews[label] = review_choices([dict(root=r) for r in rows],choices,out / 'choice-cache.jsonl')
                save_json(out / (label+'-review.json'),reviews[label])
            means = {name:[statistics.mean(reviews[name+'-'+str(i)]['mean_regret'][j] for i in [1,2])
                for j in [0,1]] for name in ['baseline','prototype']}
            new_errors, new_mates = [], []
            for i in [1,2]:
                for a,b in zip(reviews[f'baseline-{i}']['records'],reviews[f'prototype-{i}']['records'],strict=True):
                    assert a['id'] == b['id']
                    if max(a['regret']) < 200 and min(b['regret']) >= 200:
                        new_errors.append(dict(pass_number=i,id=a['id']))
                    if b['mate_loss'] and not a['mate_loss']:
                        new_mates.append(dict(pass_number=i,id=a['id']))
            no_regression = all(b <= a for a,b in zip(means['baseline'],means['prototype'],strict=True))
            improves = all(b < a for a,b in zip(means['baseline'],means['prototype'],strict=True)) or depth_gain >= .25
            passed = not new_errors and not new_mates and no_regression and improves
            teacher = dict(mean_regret=means,new_errors=new_errors,new_mates=new_mates,
                newly_requested_nodes=sum(r['new_teacher_nodes'] for r in reviews.values()))
        else:
            teacher = None
        assert manifest(base) == before and manifest(prototype) == after
        result = dict(status='complete',passed=passed,promotion=False,cheap_pass=cheap,
            mean_depth=depth,depth_gain=depth_gain,error_repeats=repeats,teacher_review=teacher,
            scope='Exposed development positions and host-dependent timing. A pass permits a small match screen, not a rating or automatic release.')
        save_json(out / 'gate.json',result)
        context.update(status='complete',passed=passed,end_memory=memory())
        print(json.dumps(result),flush=True)
    except BaseException as error:
        context.update(status='failed',error=repr(error))
        raise
    finally:
        save_json(out / 'context.json',context)


if __name__ == '__main__':
    main()
