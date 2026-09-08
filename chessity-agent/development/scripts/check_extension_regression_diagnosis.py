"""Run the two frozen branch traces serially with capacity and process-tree bounds."""
import json

from scripts.alien_rating_ladder import save_json, sha256
from scripts.improvement_check_extension_gate_recovered import child
from scripts.overnight_capacity import wait_for_capacity
from training.fastchess_data import ROOT


def main():
    out = ROOT / 'runs/improvement-loop-20260907/cycle-24'
    path = out / 'context.json'
    if path.exists():
        raise ValueError('No repeated diagnosis')
    preparation = json.loads((out / 'preparation.json').read_text())
    for name, digest in preparation['source_files'].items():
        assert sha256(ROOT / name) == digest
    result = dict(status='running', completed=[], preparation_sha256=sha256(out / 'preparation.json'))
    save_json(path, result)
    try:
        for variant in ['baseline', 'prototype']:
            wait_for_capacity(out / (variant + '-capacity.json'))
            child(['-m', 'scripts.check_extension_regression_trace', '--variant', variant],
                  out / (variant + '.log'), timeout=300)
            report = json.loads((out / (variant + '.json')).read_text())
            assert report['status'] == 'complete' and len(report['records']) == 12
            result['completed'].append(variant)
            save_json(path, result)
        result['status'] = 'complete'
    except BaseException as error:
        result.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(path, result)


if __name__ == '__main__':
    main()
