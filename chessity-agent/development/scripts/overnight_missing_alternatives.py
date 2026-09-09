"""Independently verify ambiguous alternatives and label two critical capture branches."""

import argparse
import hashlib
import json
from pathlib import Path

import chess

from scripts.feedback_matches_windows import feedback_path
from scripts.feedback_position_plan import start_group
from scripts.overnight_geometry_trial import ROOT, check_stop, digest, save
from scripts.overnight_value_labels import duplicate, restore

OUT = ROOT / 'runs/overnight-20260909/missing-alternatives-01'


def prepare():
    assert not OUT.exists(), 'Preserve prior attempts.'
    folder = feedback_path(ROOT / 'runs/improvement-loop-20260907/overnight9-countercheck-leaf-01-rated-2400/rated-prototype')
    sources = sorted(folder.glob('postgame-feedback/reviews/games/*/review.json'))
    selected = [(p, json.loads(p.read_text(encoding='utf-8'))) for p in sources]
    source, doc = next((p, d) for p, d in selected if d['own_moves'] > 0)
    assert doc['status'] == 'complete' and doc['identity']['game']['source_game_id'] == '1'
    row = next(r for r in doc['rows'] if r['fullmove'] == 33)
    assert row['san'] == 'Bxc4' and row['label'] == 'major_mistake' and row['policy_target'] is None
    assert min(v['best']['cp'] for v in row['labels']) >= -300
    roots = [dict(id='new-2400-white-33', source=str(source.relative_to(feedback_path(ROOT))),
        group=start_group(doc['identity']['game']), split='validation', **row)]
    donor = ROOT / 'runs/overnight-20260909/countercheck-leaf-01'
    prep = json.loads((donor / 'preparation.json').read_text(encoding='utf-8'))
    state = json.loads((donor / 'state.json').read_text(encoding='utf-8'))
    old_root = next(r for r in prep['roots'] if r['id'] == 'd65-game-2-move-35')
    review = next(r for r in state['review'] if r['id'] == old_root['id'])
    board = restore(old_root)
    played = next(c for c in review['choices'] if c['label'] == 'prototype')
    assert played['uci'] == 'f4d4' and board.san(chess.Move.from_uci(played['uci'])) == 'Qxd4'
    labels = [dict(nodes=n, best=b, played=v) for n, b, v in zip((80000, 320000), review['best'], played['values'], strict=True)]
    group = start_group(dict(start_fen=board.root().fen()))
    assert group == roots[0]['group'], 'Both critical cases are the exposed D65 group.'
    roots.append(dict(id='d65-black-35-capture', source=str((donor / 'state.json').relative_to(ROOT)),
        group=group, split='validation', start_fen=old_root['start_fen'], history=old_root['history'],
        fen=old_root['fen'], ply=len(old_root['history']), fullmove=35, san='Qxd4', played=played['uci'],
        labels=labels, reward=None, policy_target=None))
    prior_path = ROOT / 'runs/overnight-20260909/feedback-plan-countercheck-01/preparation.json'
    prior = json.loads(prior_path.read_text(encoding='utf-8'))
    previous_keys = {r['duplicate_key'] for r in prior['targets']}
    previous_paths = [ROOT / p for p in (
        'runs/overnight-20260909/value-labels-02/preparation.json',
        'runs/overnight-20260909/development-values-01/preparation.json',
        'runs/overnight-20260909/rule-value-01/preparation.json')]
    for path in previous_paths:
        item = json.loads(path.read_text(encoding='utf-8'))
        previous_keys.update(r.get('duplicate_key', r.get('key')) for r in item.get('targets', item.get('rows', [])))
    previous_keys.discard(None)
    for root in roots:
        board = restore(root)
        root['alternatives'] = sorted({v['best']['pv'][0] for v in root['labels']})
        assert len(root['alternatives']) <= 2
        assert all(chess.Move.from_uci(m) in board.legal_moves for m in root['alternatives'])
    files = [source, *map(feedback_path, previous_paths), feedback_path(prior_path),
        feedback_path(donor / 'preparation.json'), feedback_path(donor / 'state.json'),
        feedback_path(Path(__file__)), feedback_path(ROOT / 'docs/OVERNIGHT_MISSING_ALTERNATIVES_20260909.md')]
    OUT.mkdir()
    save(OUT / 'preparation.json', dict(roots=roots, previous_keys=sorted(previous_keys),
        source_sha256={str(p.relative_to(feedback_path(ROOT))): digest(p) for p in files},
        maximum_teacher_nodes=8000000,
        scope='Two exposed D65 development roots; independently verify action alternatives and label descendants. Retain validation attribution; no value fit, policy mutation, promotion or Elo.'))


def run():
    from scripts.overnight_capacity import wait_for_capacity
    from training.game_feedback import CachedTeacher

    prep_path = OUT / 'preparation.json'
    prep = json.loads(prep_path.read_text(encoding='utf-8'))
    assert all(digest(feedback_path(ROOT / p)) == h for p, h in prep['source_sha256'].items())
    assert not (OUT / 'state.json').exists()
    check_stop()
    wait_for_capacity(OUT / 'capacity.json', minimum_memory_mb=1400, wait_seconds=120)
    teacher = CachedTeacher(ROOT / 'data/postgame-feedback/cache-v1', OUT)
    report = dict(status='running', preparation_sha256=digest(prep_path), roots=[], rows=[], exclusions=[])
    seen = set(prep['previous_keys'])
    try:
        for root in prep['roots']:
            check_stop()
            board = restore(root)
            choices = {}
            for move in sorted({root['played'], *root['alternatives']}):
                choices[move] = [teacher.analyse(board, n, chess.Move.from_uci(move)) for n in (80000, 320000)]
            references = [max([root['labels'][i]['best']['cp']] +
                [v[i]['cp'] for v in choices.values() if v[i]['cp'] is not None]) for i in range(2)]
            verified = []
            for move in root['alternatives']:
                values = choices[move]
                finite = all(v['cp'] is not None and v['mate'] is None for v in values + choices[root['played']])
                if finite:
                    gaps = [b - v['cp'] for b, v in zip(references, values, strict=True)]
                    improvement = [v['cp'] - p['cp'] for v, p in zip(values, choices[root['played']], strict=True)]
                    if max(gaps) <= 50 and min(improvement) >= 70 and abs(values[0]['cp'] - values[1]['cp']) <= 100:
                        verified.append(move)
            report['roots'].append(dict(id=root['id'], played=root['san'], original_policy_target=root['policy_target'],
                values=choices, best_available_cp=references,
                verified_safe_alternatives=[dict(uci=m, san=board.san(chess.Move.from_uci(m))) for m in verified],
                note='Multiple verified safe alternatives are permitted; no single original best move was invented.'))
            for branch in sorted({root['played'], *verified}):
                child = restore(root)
                for depth, uci in enumerate(choices[branch][-1]['pv'][:6], 1):
                    child.push_uci(uci)
                    if depth not in (2, 4, 6):
                        continue
                    key = duplicate(child)
                    if child.is_check() or child.is_game_over(claim_draw=True) or child.is_repetition(2) or child.halfmove_clock >= 70 or key in seen:
                        report['exclusions'].append(dict(root=root['id'], branch=branch, depth=depth,
                            reason='check/terminal/repetition/draw-clock/prior-or-mirror-duplicate'))
                        continue
                    seen.add(key)
                    check_stop()
                    labels = [teacher.analyse(child, n) for n in (80000, 320000)]
                    cp = [v['cp'] for v in labels]
                    eligible = (all(v is not None for v in cp) and all(v['mate'] is None for v in labels)
                        and max(map(abs, cp)) <= 1500 and abs(cp[0] - cp[1]) <= 100)
                    identity = hashlib.sha256(json.dumps([root['id'], branch, depth, child.fen()]).encode()).hexdigest()
                    report['rows'].append(dict(id=identity, group=root['group'], split=root['split'],
                        root_id=root['id'], root_ply=root['ply'], branch=branch, descendant_plies=depth,
                        start_fen=child.root().fen(), history=[m.uci() for m in child.move_stack], fen=child.fen(),
                        duplicate_key=key, teacher=labels, eligible=eligible,
                        target_stm_cp=sum(cp) / 2 if eligible else None,
                        note='Independent endpoint value; not copied from the parent action or reward.'))
                    assert teacher.requested_nodes <= prep['maximum_teacher_nodes']
                    report['requested_teacher_nodes'] = teacher.requested_nodes
                    save(OUT / 'state.json', report)
        report.update(status='complete', eligible=sum(r['eligible'] for r in report['rows']),
            training_performed=False, selected_version=None)
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        teacher.close()
        report['requested_teacher_nodes'] = teacher.requested_nodes
        save(OUT / 'state.json', report)
        print(json.dumps({k:v for k,v in report.items() if k not in ('rows','exclusions')}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    prepare() if parser.parse_args().prepare else run()
