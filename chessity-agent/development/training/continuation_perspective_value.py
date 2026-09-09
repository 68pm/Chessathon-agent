"""Same colour-complete data and fit, one explicit perspective-difference change."""
import argparse
import json
import shutil
from pathlib import Path

from scripts.continuation_common import ROOT,RUN,check_stop,digest,manifest,save
from scripts.overnight_capacity import wait_for_capacity
from training import continuation_curriculum_value as base
from training import continuation_colour_value as colour
from training.daytime_antisymmetric import forward,gradients

OUT=RUN/'curriculum-value-03'
PRIOR=RUN/'curriculum-value-02'


def prepare():
    check_stop();assert not OUT.exists()
    wait_for_capacity(RUN/'curriculum-value-capacity-03.json',minimum_memory_mb=1400,wait_seconds=0)
    old=json.loads((PRIOR/'state.json').read_text())
    assert old['status']=='complete' and not old['passed'] and old['decision']=='reject_exposed_colour_development'
    assert not (RUN/'gm-colour-values-01/reserved_test.json').exists()
    prep=json.loads((PRIOR/'preparation.json').read_text())
    assert digest(PRIOR/'dataset.npz')==prep['dataset_sha256']
    assert manifest(ROOT/prep['candidate'])==prep['candidate_files']
    assert all(digest(Path(p))==h for p,h in prep['sources'].items())
    OUT.mkdir();shutil.copyfile(PRIOR/'dataset.npz',OUT/'dataset.npz')
    sources=[Path(__file__),Path(base.__file__),Path(colour.__file__),PRIOR/'preparation.json',
        PRIOR/'state.json',PRIOR/'dataset.npz',ROOT/'training/daytime_antisymmetric.py',
        ROOT/'tests/test_continuation_perspective_value.py',ROOT/'tests/test_daytime_antisymmetric.py',
        ROOT/'docs/CONTINUATION_PERSPECTIVE_VALUE_PLAN_20260909.md']
    prep.update(sources={str(p):digest(p) for p in sources},
        architecture='Half-difference of two 768x16 clipped-ReLU piece perspectives; fixed signed output weights',
        runtime_equation='0.5*(clip(accumulator[stm],0,1)-clip(accumulator[opponent],0,1)) dot output',
        no_synthetic_turn_labels=True,previous_dataset_sha256=digest(PRIOR/'dataset.npz'))
    save(OUT/'preparation.json',prep)
    print('Prepared identical data with sixteen-unit perspective-difference residual',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['prepare','fit','exposed','label_reserved','reserved'],required=True)
    mode=parser.parse_args().mode
    try:
        if mode=='prepare':prepare()
        elif mode=='fit':
            base.OUT=OUT;base.forward=forward;base.gradients=gradients;base.fit()
        elif mode=='label_reserved':
            from scripts import continuation_colour_labels as labels
            labels.FIT=OUT;labels.label('reserved_test')
        else:
            colour.OUT=OUT;colour.forward=forward;colour.evaluate(mode=='reserved')
    except BaseException as error:
        if OUT.exists():
            path=OUT/'state.json';state=json.loads(path.read_text()) if path.exists() else {}
            state.update(status='failed',passed=False,error=repr(error));save(path,state)
        raise
