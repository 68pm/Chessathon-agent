"""Test watchdog phase separation using tiny disposable Python children."""
import json

import pytest

from scripts.validate_package_staged import run_probe


def test_ready_starts_a_separate_post_initialisation_deadline(tmp_path):
    # Combined duration exceeds the startup budget but each separate phase fits.
    program = "import time,json;time.sleep(.2);print(json.dumps(dict(event='ready',init_ms=200)),flush=True);time.sleep(1.);print(json.dumps(dict(legal_calls=2)),flush=True)"
    result,state = run_probe(program,tmp_path,[],tmp_path/'success.json',startup_seconds=1.,ready_seconds=2.)
    assert result['legal_calls']==2 and state['status']=='complete'
    assert state['elapsed_seconds']>1.


def test_missing_ready_cannot_escape_startup_deadline(tmp_path):
    out=tmp_path/'slow.json'
    with pytest.raises(TimeoutError,match='startup'):
        run_probe('import time;time.sleep(3)',tmp_path,[],out,startup_seconds=.6,ready_seconds=2.)
    saved=json.loads(out.with_suffix('.progress.json').read_text())
    assert saved['status']=='failed' and saved['stage']=='startup'


def test_calls_cannot_escape_post_ready_deadline(tmp_path):
    program="import time,json;print(json.dumps(dict(event='ready',init_ms=1)),flush=True);time.sleep(3)"
    out=tmp_path/'calls.json'
    with pytest.raises(TimeoutError,match='move-and-feature-checks'):
        run_probe(program,tmp_path,[],out,startup_seconds=2.,ready_seconds=.6)
    assert json.loads(out.with_suffix('.progress.json').read_text())['init_ms']==1
