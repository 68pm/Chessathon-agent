"""Fit one bounded position-context correction, with separate colour checks."""
import os
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'
import argparse
import json
from pathlib import Path
import chess
import numpy as np
from scripts.progression_common import ROOT, RUN, BASE, check_stop, digest, manifest, save
from scripts.overnight_capacity import wait_for_capacity
from scripts.overnight_value_labels import restore, duplicate
from training.progression_context_head import CAPS, features, predict, solve_box

OUT = RUN / 'context-value-01'
PRIOR = ROOT / 'runs/continuation-20260909/curriculum-value-02'
DESC = RUN / 'loss-descendants-01/teacher.json'
GM = ROOT / 'runs/continuation-20260909/gm-colour-values-01'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def prepare():
    check_stop()
    assert not OUT.exists()
    wait_for_capacity(RUN / 'context-value-capacity.json', minimum_memory_mb=1400, wait_seconds=120)
    prior = read(PRIOR / 'preparation.json')
    assert digest(PRIOR / 'dataset.npz') == prior['dataset_sha256']
    assert manifest(BASE) == prior['candidate_files']
    assert digest(ROOT.parent / 'chessity-agent.zip') == prior['selected_sha256']
    assert not (GM / 'reserved_test.json').exists()
    protected = set(read(GM / 'preparation.json')['protected_full_game_keys'])
    with np.load(PRIOR / 'dataset.npz', allow_pickle=False) as data:
        base, cp, split, kind = [data[k].tolist() for k in ('base', 'cp', 'split', 'kind')]
    rows = list(prior['rows'])
    assert len(rows) == len(base) == 13386
    used = {row['key'] for row in rows}
    assert not used & protected
    teacher = read(DESC)
    assert teacher['status'] == 'complete'
    added = []
    for row in teacher['rows']:
        q = row.get('quiescence', {})
        if not (row['eligible'] and q.get('complete') and q.get('score_stm_cp') is not None
                and abs(q['score_stm_cp'] - row['static_stm_cp']) <= 75):
            continue
        board = restore(row); key = duplicate(board)
        if key in used or key in protected:
            continue
        used.add(key)
        rows.append(dict(fen=row['fen'], key=key, source_id=row['id'], kind='latest',
                         group=row['root_id'], split=0, start_fen=row['start_fen'], history=row['history']))
        added.append(row['id']); base.append(row['static_stm_cp']); cp.append(row['target_stm_cp'])
        split.append(0); kind.append('latest')
    assert len(added) >= 12
    x, white = [], []
    for index, row in enumerate(rows):
        if index % 256 == 0:
            check_stop()
        board = chess.Board(row['fen'])
        assert board.is_valid() and duplicate(board) == row['key']
        x.append(features(board)); white.append(board.turn)
    OUT.mkdir()
    np.savez_compressed(OUT / 'dataset.npz', x=x, base=base, cp=cp, split=split, kind=kind, white=white)
    sources = [Path(__file__), ROOT / 'training/progression_context_head.py',
        ROOT / 'tests/test_progression_context_head.py', ROOT / 'scripts/progression_common.py',
        PRIOR / 'preparation.json', PRIOR / 'dataset.npz', DESC, GM / 'preparation.json']
    save(OUT / 'preparation.json', dict(rows=rows, sources={str(p): digest(p) for p in sources},
        dataset_sha256=digest(OUT / 'dataset.npz'), candidate_files=manifest(BASE),
        selected_sha256=digest(ROOT.parent / 'chessity-agent.zip'), protected_keys=sorted(protected),
        added_descendants=added, penalty=2000., coefficient_caps=CAPS.tolist(),
        training_weights={'broad': 1., 'gm': 2., 'recent': 8., 'latest': 8.},
        scope='One original three-feature position-residual fit. Existing and latest quiet '
              'independently labelled descendants; broad development set already exposed. '
              'Includes the exposed v1.56 35.h5 development loss; no reserved Italian leaf labels used for fitting.'))
    print(json.dumps(dict(prepared=len(rows), new_quiet_descendants=len(added))), flush=True)


def verify(prep):
    assert all(digest(Path(path)) == expected for path, expected in prep['sources'].items())
    assert digest(OUT / 'dataset.npz') == prep['dataset_sha256']
    assert manifest(BASE) == prep['candidate_files']
    assert digest(ROOT.parent / 'chessity-agent.zip') == prep['selected_sha256']


def metrics(base, cp, residual, white):
    result = {}
    for label, mask in (('white', white), ('black', ~white)):
        a, b, y = base[mask], (base + residual)[mask], cp[mask]
        result[label] = dict(n=int(mask.sum()), before_mae=float(np.mean(abs(a - y))),
            after_mae=float(np.mean(abs(b - y))), major_before=int(np.sum(abs(a - y) >= 200)),
            major_after=int(np.sum(abs(b - y) >= 200)))
    return result


def colour_passes(rows):
    return all(r['n'] >= 6 and r['after_mae'] <= r['before_mae'] and r['major_after'] <= r['major_before']
               for r in rows.values())


def fit():
    check_stop(); prep = read(OUT / 'preparation.json'); verify(prep)
    assert not (OUT / 'state.json').exists()
    with np.load(OUT / 'dataset.npz', allow_pickle=False) as data:
        x, base, cp, split, kind, white = [data[k] for k in ('x', 'base', 'cp', 'split', 'kind', 'white')]
    train, valid = split == 0, split == 1
    weights = np.array([prep['training_weights'][k] for k in kind[train]])
    coefficient = solve_box(x[train], np.clip(cp[train] - base[train], -500, 500), weights, prep['penalty'])
    save(OUT / 'value.json', dict(coefficients=coefficient.tolist(), coefficient_caps=CAPS.tolist(),
        physical_coefficients=(coefficient * CAPS).tolist(), features=['king_shelter', 'unsafe_mobility_mg', 'unsafe_mobility_eg']))
    residual = predict(x, coefficient)
    mse_before = float(np.mean(np.minimum((base[valid] - cp[valid])**2, 1000000)))
    mse_after = float(np.mean(np.minimum((base[valid] + residual[valid] - cp[valid])**2, 1000000)))
    colours = metrics(base[valid], cp[valid], residual[valid], white[valid])
    target = {}
    for label in ('gm', 'recent', 'latest'):
        selected = kind == label
        target[label] = dict(n=int(selected.sum()), before_mae=float(np.mean(abs(base[selected] - cp[selected]))),
                            after_mae=float(np.mean(abs(base[selected] + residual[selected] - cp[selected]))))
    passed = (mse_after <= .99 * mse_before and colour_passes(colours)
              and all(r['after_mae'] <= r['before_mae'] for r in target.values())
              and target['latest']['after_mae'] <= .95 * target['latest']['before_mae'])
    state = dict(status='weights_frozen_before_exposed_check' if passed else 'complete', passed=False,
        development_fit_passed=bool(passed), coefficients=coefficient.tolist(), model_sha256=digest(OUT / 'value.json'),
        broad_mse_before=mse_before, broad_mse_after=mse_after, colours=colours, target_metrics=target,
        decision='needs_exposed_colour_check' if passed else 'reject_development_fit')
    save(OUT / 'state.json', state)
    print(json.dumps(state), flush=True)


def exposed():
    from training.continuation_curriculum_value import classical
    from training.rule_value import arrays
    check_stop(); prep = read(OUT / 'preparation.json'); verify(prep)
    state = read(OUT / 'state.json')
    assert state['status'] == 'weights_frozen_before_exposed_check'
    assert digest(OUT / 'value.json') == state['model_sha256']
    sources = [ROOT / 'runs/continuation-20260909/gm-values-01/reserved_test.json',
               ROOT / 'runs/continuation-20260909/curriculum-black-check-01/state.json']
    fn = classical(BASE); values = []
    used = {r['key'] for r in prep['rows']}
    for path in sources:
        for row in read(path)['rows']:
            if not row['eligible']:
                continue
            board = restore(row)
            assert duplicate(board) not in used
            values.append((fn(*arrays(board), False), row['target_stm_cp'],
                           predict(features(board), state['coefficients']), board.turn))
    array = np.array(values)
    colours = metrics(array[:, 0], array[:, 1], array[:, 2], array[:, 3].astype(bool))
    passed = colour_passes(colours)
    save(OUT / 'exposed-colours.json', dict(status='complete', passed=passed, colours=colours,
        sources={str(p): digest(p) for p in sources}, model_sha256=state['model_sha256']))
    state.update(status='weights_frozen_before_fresh_labels' if passed else 'complete',
                 decision='needs_fresh_colour_labels' if passed else 'reject_exposed_colours')
    save(OUT / 'state.json', state)
    print(json.dumps(dict(passed=passed, colours=colours, decision=state['decision'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('prepare', 'fit', 'exposed'), required=True)
    args = parser.parse_args()
    globals()[args.mode]()
