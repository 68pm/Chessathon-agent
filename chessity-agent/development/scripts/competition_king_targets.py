"""One frozen queenless king-target trial on the newly reviewed real games."""
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
REVIEW = ROOT / 'runs/competition-review-20260908'
OUT = ROOT / 'runs/competition-king-targets-20260908'


def verify():
    prep = json.loads((OUT / 'preparation.json').read_text())
    for path, digest in prep['sources'].items():
        assert sha256(ROOT / path) == digest, path
    assert manifest(OUT / 'prototype') == prep['prototype_files']
    return prep


def worker():
    verify()
    path = OUT / 'prototype.json'
    assert not path.exists()
    report = dict(status='initializing', pid=os.getpid(), records=[])
    save_json(path, report)
    try:
        stopped()
        tick = time.perf_counter()
        sys.path.insert(0, str(OUT / 'prototype'))
        import agent

        core = sys.modules['engine.compiled_core']
        assert Path(core.__file__).resolve() == OUT / 'prototype/engine/compiled_core.py'
        report['init_seconds'] = time.perf_counter() - tick
        save_json(path, report)
        assert report['init_seconds'] <= 90
        agent._search.policy = None
        rows = [json.loads(line) for line in (REVIEW / 'targets.jsonl').read_text().splitlines()]
        assert len(rows) == 14
        report['status'] = 'critical-position-probes'
        for row in rows:
            stopped()
            board = restore(row)
            stack = list(board.move_stack)
            for name in ['ttkey', 'ttcontext', 'ttdata', 'killers', 'history']:
                getattr(agent._search, name).fill(0)
            tick = time.perf_counter()
            result = agent._search.run(board, 1., 1., max_depth=64)
            elapsed = time.perf_counter() - tick
            restored = board.fen() == row['fen'] and board.move_stack == stack
            legal = result.move in board.legal_moves
            report['records'].append(dict(id=row['id'], uci=result.move.uci(), san=board.san(result.move),
                score=result.score, depth=result.depth, nodes=result.nodes, seconds=elapsed,
                legal=legal, restored=restored))
            save_json(path, report)
            assert restored and legal and result.depth >= 1 and elapsed <= 1.25
        verify()
        report['status'] = 'complete'
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(path, report)


def review():
    import chess

    from scripts.improvement_audit import evaluate
    from scripts.magnus_benchmark import SF
    from scripts.overnight_capacity import wait_for_capacity
    from training.puzzle_verifier import Verifier

    verify()
    path = OUT / 'choice-review.json'
    assert not path.exists()
    roots = json.loads((REVIEW / 'teacher.json').read_text())['records']
    previous = json.loads((REVIEW / 'choice-review.json').read_text())['records']
    probes = json.loads((OUT / 'prototype.json').read_text())['records']
    report = dict(status='running', records=[], requested_nodes=0, maximum_requested_nodes=5600000,
        teacher_sha256=sha256(SF))
    save_json(path, report)
    wait_for_capacity(OUT / 'teacher-launch-capacity.json')
    stopped()
    verifier = Verifier(SF)
    try:
        for row in roots:
            board = restore(row)
            chosen = next(item for item in probes if item['id'] == row['id'])
            old = next(item for item in previous if item['id'] == row['id'])['versions']
            values = []
            for i, budget in enumerate([80000, 320000]):
                stopped()
                ref = row['verification'][i]
                cached = next((v['analysis'][i] for v in old.values() if v['uci'] == chosen['uci']), None)
                if cached is not None:
                    value = cached
                elif chosen['uci'] == row['played']:
                    value = ref['played']
                elif chosen['uci'] == ref['best']['pv'][0]:
                    value = ref['best']
                else:
                    report['requested_nodes'] += budget
                    assert report['requested_nodes'] <= report['maximum_requested_nodes']
                    save_json(path, report)
                    value = evaluate(verifier.engine, board, budget, chess.Move.from_uci(chosen['uci']))
                values.append(value)
            regret = [max(0, ref['best']['cp'] - val['cp'])
                if ref['best']['cp'] is not None and val['cp'] is not None else None
                for ref, val in zip(row['verification'], values, strict=True)]
            report['records'].append(dict(id=row['id'], baseline=old['v1.53'],
                prototype=dict(chosen, analysis=values, regret=regret)))
            save_json(path, report)
        verify()
        report['status'] = 'complete'
    finally:
        verifier.close()
        save_json(path, report)


def gate():
    rows = json.loads((OUT / 'choice-review.json').read_text())['records']
    finite = [r for r in rows if all(v is not None for label in ['baseline', 'prototype'] for v in r[label]['regret'])]
    means = {label: [statistics.mean(r[label]['regret'][i] for r in finite) for i in range(2)]
        for label in ['baseline', 'prototype']}
    def major(row):
        return all(v is not None and v >= 200 for v in row['regret'])

    def mate_loss(row):
        return any(v.get('mate') is not None and v['mate'] < 0 for v in row['analysis'])
    new_major = [r['id'] for r in rows if major(r['prototype']) and not major(r['baseline'])]
    new_mate = [r['id'] for r in rows if mate_loss(r['prototype']) and not mate_loss(r['baseline'])]
    repairs = [r['id'] for r in finite if all(r['baseline']['regret'][i] - r['prototype']['regret'][i] >= 100 for i in range(2))]
    counts = {label: sum(major(r[label]) for r in rows) for label in ['baseline', 'prototype']}
    draw_improved = all(v is not None and v <= 50 for v in rows[-1]['prototype']['regret'])
    passed = (draw_improved and len(finite) >= 13 and bool(repairs) and not new_major and not new_mate
        and counts['prototype'] < counts['baseline']
        and all(a < b for a, b in zip(means['prototype'], means['baseline'], strict=True)))
    save_json(OUT / 'gate.json', dict(passed=passed, common_finite=len(finite), mean_regret=means,
        paired_major_errors=counts, new_major=new_major, new_mate=new_mate, repaired_100cp=repairs,
        completed_depths={label: [r[label]['depth'] for r in rows] for label in ['baseline', 'prototype']},
        draw_case=rows[-1], draw_improved=draw_improved, limitation='Exposed development positions; no Elo or full-game claim.'))


def main():
    from scripts.improvement_king_coordination_gate import child
    from scripts.overnight_capacity import wait_for_capacity

    verify()
    path = OUT / 'context.json'
    assert not path.exists(), 'No unchanged retry'
    state = dict(status='running', pid=os.getpid(), completed=[])
    save_json(path, state)
    try:
        for stage in ['tests', 'worker', 'review']:
            stopped()
            state['stage'] = stage
            save_json(path, state)
            wait_for_capacity(OUT / (stage + '-capacity.json'))
            args = ['-X', 'utf8', '-m', 'pytest', 'tests/test_competition_king_targets.py', '-q'] if stage == 'tests' else [
                '-X', 'utf8', '-m', 'scripts.competition_king_targets', '--stage', stage]
            child(args, OUT / (stage + '.log'), timeout=360)
            state['completed'].append(stage)
        gate()
        verify()
        state.update(status='complete', stage='awaiting_critique')
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(path, state)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['worker', 'review'])
    args = parser.parse_args()
    if args.stage == 'worker':
        worker()
    elif args.stage == 'review':
        review()
    else:
        main()
