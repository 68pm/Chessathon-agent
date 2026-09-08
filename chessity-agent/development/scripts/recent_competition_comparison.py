"""Bounded independent review and equal-clock old/current probes on new real games."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import manifest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/competition-review-20260908'


def stopped():
    if any((ROOT / flag).exists() for flag in ['STOP_TRAINING', 'STOP_BENCHMARK']):
        raise InterruptedError('User stop flag')


def verify():
    prep = json.loads((OUT / 'preparation.json').read_text())
    for path, digest in prep['sources'].items():
        assert sha256(ROOT / path) == digest
    for label, spec in prep['candidates'].items():
        assert manifest(ROOT / spec['path']) == spec['files'], label
    assert sha256(OUT / 'targets.jsonl') == prep['targets_sha256']
    return prep


def restore(row):
    import chess

    board = chess.Board(row['start_fen'])
    for uci in row['history']:
        board.push_uci(uci)
    assert board.fen() == row['fen'] and board.is_valid()
    return board


def worker(label):
    prep = verify()
    candidate = ROOT / prep['candidates'][label]['path']
    path = OUT / (label + '.json')
    assert not path.exists()
    report = dict(status='initializing', pid=os.getpid(), candidate=str(candidate), records=[])
    save_json(path, report)
    try:
        stopped()
        tick = time.perf_counter()
        sys.path.insert(0, str(candidate.resolve()))
        import agent

        core = sys.modules['engine.compiled_core']
        assert Path(core.__file__).resolve() == (candidate / 'engine/compiled_core.py').resolve()
        report['init_seconds'] = time.perf_counter() - tick
        save_json(path, report)
        assert report['init_seconds'] <= 90
        agent._search.policy = None
        rows = [json.loads(line) for line in (OUT / 'targets.jsonl').read_text().splitlines()]
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
                repeats_played=result.move.uci() == row['played'], legal=legal, restored=restored))
            save_json(path, report)
            assert restored and legal and result.depth >= 1 and elapsed <= 1.25
        verify()
        report['status'] = 'complete'
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(path, report)


def teacher(choices=False):
    import chess

    from scripts.improvement_audit import evaluate
    from scripts.improvement_phase_report import error_signals
    from scripts.magnus_benchmark import SF
    from scripts.overnight_capacity import wait_for_capacity
    from training.puzzle_verifier import Verifier

    verify()
    name = 'choice-review' if choices else 'teacher'
    path = OUT / (name + '.json')
    assert not path.exists()
    report = dict(status='running', pid=os.getpid(), records=[], requested_nodes=0,
        maximum_requested_nodes=11200000, teacher_sha256=sha256(SF))
    save_json(path, report)
    wait_for_capacity(OUT / (name + '-launch-capacity.json'))
    stopped()
    verifier = Verifier(SF)
    try:
        def evaluate_one(board, budget, move=None):
            stopped()
            report['requested_nodes'] += budget
            assert report['requested_nodes'] <= report['maximum_requested_nodes']
            save_json(path, report)
            return evaluate(verifier.engine, board, budget, move)

        if not choices:
            roots = [json.loads(line) for line in (OUT / 'targets.jsonl').read_text().splitlines()]
            for row in roots:
                board = restore(row)
                pairs = []
                for budget in [80000, 320000]:
                    best = evaluate_one(board, budget)
                    played = best if best['pv'][0] == row['played'] else evaluate_one(board, budget, chess.Move.from_uci(row['played']))
                    pairs.append(dict(best=best, played=played))
                record = dict(row, verification=pairs)
                record['signals'] = error_signals(record)
                report['records'].append(record)
                save_json(path, report)
        else:
            roots = json.loads((OUT / 'teacher.json').read_text())['records']
            probes = {label: json.loads((OUT / (label + '.json')).read_text())['records'] for label in ['v1.41', 'v1.53']}
            cache = {}
            for row in roots:
                board = restore(row)
                records = {}
                for label in ['v1.41', 'v1.53']:
                    chosen = next(item for item in probes[label] if item['id'] == row['id'])
                    values = []
                    for i, budget in enumerate([80000, 320000]):
                        ref = row['verification'][i]
                        key = (row['id'], chosen['uci'], budget)
                        if chosen['uci'] == row['played']:
                            value = ref['played']
                        elif chosen['uci'] == ref['best']['pv'][0]:
                            value = ref['best']
                        elif key in cache:
                            value = cache[key]
                        else:
                            value = evaluate_one(board, budget, chess.Move.from_uci(chosen['uci']))
                            cache[key] = value
                        values.append(value)
                    records[label] = dict(chosen, analysis=values,
                        regret=[max(0, ref['best']['cp'] - val['cp'])
                            if ref['best']['cp'] is not None and val['cp'] is not None else None
                            for ref, val in zip(row['verification'], values, strict=True)])
                report['records'].append(dict(id=row['id'], round=row['round'], original_move=row['move'],
                    phase=row['phase'], versions=records))
                save_json(path, report)
        verify()
        report['status'] = 'complete'
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        verifier.close()
        save_json(path, report)


def main():
    from scripts.improvement_king_coordination_gate import child
    from scripts.overnight_capacity import wait_for_capacity

    verify()
    path = OUT / 'context.json'
    assert not path.exists(), 'Preserve every attempt; no unchanged retry'
    report = dict(status='running', pid=os.getpid(), completed=[])
    save_json(path, report)
    try:
        for stage in ['teacher', 'v1.41', 'v1.53', 'choice-review']:
            stopped()
            report['stage'] = stage
            save_json(path, report)
            wait_for_capacity(OUT / (stage + '-capacity.json'))
            args = ['-m', 'scripts.recent_competition_comparison', '--stage', stage]
            child(args, OUT / (stage + '.log'), timeout=360)
            assert json.loads((OUT / (stage + '.json')).read_text())['status'] == 'complete'
            report['completed'].append(stage)
            save_json(path, report)
        verify()
        report.update(status='complete', stage='awaiting_critique')
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(path, report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['teacher', 'v1.41', 'v1.53', 'choice-review'])
    args = parser.parse_args()
    if args.stage in ['v1.41', 'v1.53']:
        worker(args.stage)
    elif args.stage:
        teacher(args.stage == 'choice-review')
    else:
        main()
