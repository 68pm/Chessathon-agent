"""Export independently labelled descendants without silently fitting/clipping."""
import argparse
import json
from pathlib import Path

import chess
import numpy as np

from engine.features import encode
from scripts.alien_rating_ladder import save_json, sha256


def classify(leaf):
    board = chess.Board(leaf['start_fen'])
    for move in leaf['history']:
        board.push_uci(move)
    assert board.fen() == leaf['fen'] and board.is_valid()
    labels = leaf.get('teacher', [])
    reasons = []
    if leaf['terminal']:
        reasons.append('terminal; preserve as search regression, not static value target')
    if board.is_check():
        reasons.append('in check; search must resolve evasions before static evaluation')
    if board.is_repetition(2) or board.halfmove_clock >= 70 or board.can_claim_draw():
        reasons.append('history-sensitive; the 768-piece input does not encode the draw context')
    if board.castling_rights or board.has_legal_en_passant():
        reasons.append('castling/en-passant rights are absent from the 768-piece input')
    finite = len(labels) == 2 and all(v['cp'] is not None and v['mate'] is None for v in labels)
    if not finite:
        reasons.append('no paired finite independent value labels')
    elif abs(labels[0]['cp'] - labels[1]['cp']) > 100:
        reasons.append('teacher value changes by more than 100cp between budgets')
    factor = 1 if board.turn == leaf['root_white'] else -1
    base_stm = leaf['static_root'] * factor
    residual = [v['cp'] - base_stm for v in labels] if finite else None
    sparse = np.flatnonzero(encode(board)[:768]).tolist()
    return dict(id=leaf['id'], target=leaf['target'], start_fen=leaf['start_fen'],
        history=leaf['history'], fen=leaf['fen'], group=leaf['target'].split('-ply-')[0],
        split='exposed_competition_development', sparse_features_768=sparse,
        origins=leaf['origins'], value_perspective='side to move at this descendant',
        independently_evaluated_here=bool(labels), teacher=labels,
        static_stm_cp=base_stm, required_residual_stm_cp=residual,
        eligible_static_target=not reasons, excluded_reasons=reasons,
        within_legacy_125cp_range=all(abs(v) <= 125 for v in residual) if residual else None,
        within_500cp_range=all(abs(v) <= 500 for v in residual) if residual else None,
        trained=False)


def export(source, out):
    data = json.loads(source.read_text())
    assert data['status'] == 'complete'
    assert not out.exists(), 'Preserve completed and partial exports'
    out.mkdir(parents=True)
    rows = [classify(leaf) for leaf in data['leaves']]
    # Same piece input can represent different histories or hidden rights. Never
    # create conflicting scalar supervision by treating those as new examples.
    by_features = {}
    for row in rows:
        key = tuple(row['sparse_features_768'])
        by_features.setdefault(key, []).append(row)
    for group in by_features.values():
        eligible = [r for r in group if r['eligible_static_target']]
        values = [r['teacher'][1]['cp'] for r in eligible]
        if values and max(values) - min(values) > 100:
            for row in eligible:
                row['eligible_static_target'] = False
                row['excluded_reasons'].append('conflicting labels for identical 768-piece input')
        elif eligible:
            for row in eligible[1:]:
                row['eligible_static_target'] = False
                row['duplicate_of'] = eligible[0]['id']
                row['excluded_reasons'].append('duplicate 768-piece input; retained for audit, not repeated training weight')
    path = out / 'independent-descendants.jsonl'
    path.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
    accepted = [r for r in rows if r['eligible_static_target']]
    report = dict(status='complete', source_sha256=sha256(source), records=len(rows),
        eligible_static_targets=len(accepted), excluded=len(rows) - len(accepted),
        groups=sorted({r['group'] for r in accepted}),
        eligible_beyond_125cp=sum(not r['within_legacy_125cp_range'] for r in accepted),
        eligible_beyond_500cp=sum(not r['within_500cp_range'] for r in accepted),
        records_sha256=sha256(path), trained=False,
        limitation='Independent labels on exposed development descendants. No fit, clipping, root-label propagation or generalisation claim.')
    save_json(out / 'manifest.json', report)
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(export(args.source, args.out)))
