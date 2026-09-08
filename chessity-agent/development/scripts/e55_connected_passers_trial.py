"""Frozen serial17-root test of the new defensive battery extension."""
import argparse
import json
import os
import statistics
import sys
import time
from pathlib import Path

from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import manifest
from scripts.recent_competition_comparison import restore, stopped

ROOT = Path(__file__).resolve().parents[1]

OUT = ROOT / 'runs/e55-connected-passers-20260908'


def verify():
    prep = json.loads((OUT / 'preparation.json').read_text())
    for p, h in prep['source_files'].items():
        assert sha256(ROOT / p) == h, p
    for label, spec in prep['candidates'].items():
        assert manifest(ROOT / spec['path']) == spec['files'], label
    assert sha256(OUT / 'roots.jsonl') == prep['roots_sha256']
    return prep


def worker(label):
    prep = verify()
    candidate = ROOT / prep['candidates'][label]['path']
    path = OUT / (label + '.json')
    assert not path.exists()
    state = dict(status='initializing', pid=os.getpid(), records=[])
    save_json(path, state)
    try:
        stopped()
        sys.path.insert(0, str(candidate))
        tick = time.perf_counter()
        import agent

        state['init_seconds'] = time.perf_counter() - tick
        save_json(path, state)
        assert state['init_seconds'] <= 90
        assert __import__('pathlib').Path(sys.modules['engine.compiled_core'].__file__).resolve() == candidate / 'engine/compiled_core.py'
        agent._search.policy = None
        rows = [json.loads(x) for x in (OUT / 'roots.jsonl').read_text().splitlines()]
        assert len(rows) == 17
        for row in rows:
            stopped()
            board = restore(row)
            stack = list(board.move_stack)
            for name in ['ttkey', 'ttcontext', 'ttdata', 'killers', 'history']:
                getattr(agent._search, name).fill(0)
            tick = time.perf_counter()
            result = agent._search.run(board, 1., 1., max_depth=64)
            elapsed = time.perf_counter() - tick
            valid = result.move in board.legal_moves and board.fen() == row['fen'] and board.move_stack == stack
            state['records'].append(dict(id=row['id'], uci=result.move.uci(), san=board.san(result.move),
                score=result.score, depth=result.depth, nodes=result.nodes, seconds=elapsed, legal_restored=valid))
            save_json(path, state)
            assert valid and result.depth >= 1 and elapsed <= 1.25
        verify()
        state['status'] = 'complete'
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(path, state)


def review():
    import chess

    from scripts.improvement_audit import evaluate
    from scripts.magnus_benchmark import SF
    from scripts.overnight_capacity import wait_for_capacity
    from training.puzzle_verifier import Verifier

    verify()
    path = OUT / 'choice-review.json'
    assert not path.exists()
    roots = [json.loads(x) for x in (OUT / 'roots.jsonl').read_text().splitlines()]
    probes = {label: {r['id']: r for r in json.loads((OUT / (label + '.json')).read_text())['records']}
              for label in ['baseline', 'prototype']}
    state = dict(status='running', records=[], requested_nodes=0, maximum_requested_nodes=13600000,
                 teacher_sha256=sha256(SF))
    save_json(path, state)
    wait_for_capacity(OUT / 'teacher-launch-capacity.json')
    teacher = Verifier(SF)
    try:
        for row in roots:
            board = restore(row)
            versions, cache = {}, {}
            for label in ['baseline', 'prototype']:
                choice = probes[label][row['id']]
                values = []
                for i, budget in enumerate([80000, 320000]):
                    stopped()
                    ref = row['verification'][i]
                    key = (choice['uci'], budget)
                    if key in cache:
                        value = cache[key]
                    elif choice['uci'] == ref['best']['pv'][0]:
                        value = ref['best']
                    elif choice['uci'] == row['played']:
                        value = ref['played']
                    else:
                        state['requested_nodes'] += budget
                        assert state['requested_nodes'] <= state['maximum_requested_nodes']
                        save_json(path, state)
                        value = evaluate(teacher.engine, board, budget, chess.Move.from_uci(choice['uci']))
                    cache[key] = value
                    values.append(value)
                regret = [max(0, ref['best']['cp'] - v['cp']) if ref['best']['cp'] is not None and v['cp'] is not None else None
                          for ref, v in zip(row['verification'], values, strict=True)]
                versions[label] = dict(**choice, analysis=values, regret=regret)
            state['records'].append(dict(id=row['id'], **versions))
            save_json(path, state)
        state['status'] = 'complete'
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        teacher.close()
        save_json(path, state)


def gate():
    rows = json.loads((OUT / 'choice-review.json').read_text())['records']
    labels = ['baseline', 'prototype']
    finite = [r for r in rows if all(v is not None for label in labels for v in r[label]['regret'])]
    def major(row):
        return all(v is not None and v >= 200 for v in row['regret'])
    def mate_loss(row):
        return any(v['mate'] is not None and v['mate'] < 0 for v in row['analysis'])
    new_major = [r['id'] for r in rows if major(r['prototype']) and not major(r['baseline'])]
    new_mate = [r['id'] for r in rows if mate_loss(r['prototype']) and not mate_loss(r['baseline'])]
    repairs = [r['id'] for r in finite if all(r['baseline']['regret'][i] - r['prototype']['regret'][i] >= 100 for i in [0, 1])]
    means = {label: [statistics.mean(r[label]['regret'][i] for r in finite) for i in [0, 1]] for label in labels}
    counts = {label: sum(major(r[label]) for r in rows) for label in labels}
    draw = next(r for r in rows if r['id'] == 'game-003-ply-052')
    draw_repaired = all(v is not None and v <= 50 for v in draw['prototype']['regret'])
    passed = draw_repaired and bool(repairs) and not new_major and not new_mate and counts['prototype'] < counts['baseline'] and all(a < b for a, b in zip(means['prototype'], means['baseline'], strict=True))
    save_json(OUT / 'gate.json', dict(passed=passed, common_finite=len(finite), mean_regret=means,
        major_errors=counts, draw_repaired=draw_repaired, repaired_100cp=repairs, new_major=new_major, new_mate=new_mate,
        draw_cases=[r for r in rows if r['id'].startswith('game-003') or r['id']=='competition-r68-ply-145'],
        new_fits=0, new_games=0, scope='Exposed development positions; not a playing-strength estimate.'))


def main():
    from scripts.improvement_king_coordination_gate import child
    from scripts.overnight_capacity import wait_for_capacity

    verify()
    path = OUT / 'context.json'
    assert not path.exists()
    state = dict(status='running', pid=os.getpid(), completed=[])
    save_json(path, state)
    try:
        for stage in ['tests', 'prototype', 'review']:
            stopped()
            state['stage'] = stage
            save_json(path, state)
            wait_for_capacity(OUT / (stage + '-capacity.json'))
            args = ['-X', 'utf8', '-m', 'pytest', 'tests/test_e55_connected_passers.py', '-q'] if stage == 'tests' else [
                '-X', 'utf8', '-m', 'scripts.e55_connected_passers_trial', '--stage', stage]
            child(args, OUT / (stage + '.log'), timeout=360)
            state['completed'].append(stage)
        gate()
        verify()
        state.update(status='complete', stage='awaiting-critique')
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(path, state)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['tests', 'prototype', 'review'])
    args = parser.parse_args()
    if args.stage == 'review':
        review()
    elif args.stage:
        worker(args.stage)
    else:
        main()
