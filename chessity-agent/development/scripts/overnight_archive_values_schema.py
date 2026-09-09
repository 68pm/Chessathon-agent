"""One fixed endpoint-label batch from the completed archived-version comparison."""

import argparse
import json
from pathlib import Path

from scripts import overnight_value_labels as labels
from scripts.feedback_matches_windows import feedback_path
from scripts.overnight_geometry_trial import ROOT, check_stop, digest, save

OUT = ROOT / 'runs/overnight-20260909/archive-values-03'
SOURCE = ROOT / 'runs/overnight-20260909/feedback-plan-archive-42-01/preparation.json'


def prepare():
    assert not OUT.exists(), 'Preserve all preparations.'
    check_stop()
    prep = json.loads(SOURCE.read_text(encoding='utf-8'))
    assert prep['status'] == 'prepared' and len(prep['targets']) == 58
    assert prep['maximum_teacher_nodes'] == 23200000
    for target in prep['targets']:
        assert target['target_stm_cp'] is None
        assert set(target) & {'teacher', 'eligible', 'target_stm_cp', 'exclusion'} == {'target_stm_cp'}
        target.pop('target_stm_cp')
        dict(**target, teacher=[], eligible=False, target_stm_cp=None, exclusion=None)

    marker = ROOT / 'runs/overnight-20260909/archive-opponent-feedback-01/state.json'
    assert json.loads(marker.read_text(encoding='utf-8'))['status'] == 'complete'
    prep['source_sha256'].update({str(p.relative_to(ROOT)):digest(p) for p in (
        SOURCE, marker, Path(__file__), ROOT / 'docs/OVERNIGHT_ARCHIVE_VALUES_SCHEMA_20260909.md', ROOT / 'runs/overnight-20260909/archive-values-02/state.json', ROOT / 'docs/OVERNIGHT_ARCHIVE_VALUES_WINDOWS_20260909.md', ROOT / 'docs/OVERNIGHT_ARCHIVE_VALUES_20260909.md')})
    prep['scope'] = 'All58 positions are exposed C09/D28 development descendants, individually labelled. Within-run split is not a fresh strength holdout. No fit, selection or Elo.'
    OUT.mkdir()
    save(OUT / 'preparation.json', prep)


def run():
    assert not (OUT / 'state.json').exists(), 'No implicit retry.'
    labels.sha = lambda path: digest(feedback_path(path))
    labels.OUT = OUT
    labels.run()
    state = json.loads((OUT / 'state.json').read_text(encoding='utf-8'))
    assert state['requested_nodes_this_process'] <= 23200000


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    prepare() if parser.parse_args().prepare else run()
