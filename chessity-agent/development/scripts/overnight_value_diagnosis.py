"""Describe the failed value fit using saved predictions only; no refit or relabelling."""

import json
from collections import defaultdict

import chess
import numpy as np

from scripts.overnight_geometry_trial import ROOT, digest, save


def run():
    source = ROOT / 'runs/overnight-20260909/rule-value-01'
    out = source.parent / 'rule-value-diagnosis-01'
    assert not out.exists()
    prep = json.loads((source / 'preparation.json').read_text(encoding='utf-8'))
    selected = [r for r in prep['rows'] if r['split'] == 1 and r['targeted']]
    with np.load(source / 'holdout-predictions.npz', allow_pickle=False) as data:
        teacher, classical, prediction = (data[k].copy() for k in ('teacher', 'classical', 'prediction'))
    assert len(selected) == len(teacher) == len(classical) == len(prediction) == 31
    rows = []
    for row, target, base, value in zip(selected, teacher, classical, prediction, strict=True):
        board = chess.Board(row['fen'])
        assert abs(row['cp'] - float(target)) < .001
        phase = sum({1: 0, 2: 1, 3: 1, 4: 2, 5: 4, 6: 0}[p.piece_type] for p in board.piece_map().values())
        stage = 'endgame' if phase <= 8 else 'opening' if board.fullmove_number <= 15 and phase >= 18 else 'middlegame'
        before, after = abs(float(target - base)), abs(float(target - value))
        rows.append(dict(source_id=row['source_id'], group=row['group'], fen=row['fen'], stage=stage,
            phase=phase, teacher=float(target), classical=float(base), prediction=float(value),
            before_error=before, after_error=after, improvement_cp=before-after,
            required_correction=float(target-base), learned_correction=float(value-base),
            target_beyond_600cp=before > 600))
    def summarize(items):
        return dict(count=len(items), before_mae=sum(r['before_error'] for r in items)/len(items),
            after_mae=sum(r['after_error'] for r in items)/len(items),
            improved=sum(r['improvement_cp'] > 0 for r in items),
            worsened=sum(r['improvement_cp'] < 0 for r in items),
            target_beyond_600cp=sum(r['target_beyond_600cp'] for r in items))
    groups, phases = defaultdict(list), defaultdict(list)
    for row in rows:
        groups[row['group']].append(row)
        phases[row['stage']].append(row)
    report = dict(status='complete', source_files={p.name: digest(p) for p in (
        source / 'preparation.json', source / 'holdout-predictions.npz', source / 'state.json')},
        overall=summarize(rows), by_stage={k: summarize(v) for k, v in phases.items()},
        by_group={k: summarize(v) for k, v in groups.items()}, rows=rows,
        scope='Post-rejection diagnosis of already evaluated holdout; no new fit, labels, game or promotion. These details are development evidence for later hypotheses, not a fresh independent validation.',
        phase_rule='Non-pawn phase N/B=1,R=2,Q=4: <=8 endgame; otherwise fullmove<=15 and phase>=18 opening; remaining middlegame.')
    out.mkdir()
    save(out / 'diagnosis.json', report)
    print(json.dumps({k:v for k,v in report.items() if k in ('status','overall','by_stage','by_group')}, indent=2))


if __name__ == '__main__':
    run()
