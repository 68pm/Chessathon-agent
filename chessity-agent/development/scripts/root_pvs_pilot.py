"""One frozen root-PVS pilot with serial, bounded production-engine workers."""
import argparse
import json
import os
import statistics
import sys
import time
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import manifest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/improvement-loop-20260907/cycle-31'


def stop_check():
    if any((ROOT / name).exists() for name in ['STOP_TRAINING', 'STOP_BENCHMARK']):
        raise InterruptedError('User stop flag')


def verify(prep):
    for label in ['baseline', 'prototype']:
        assert manifest(ROOT / prep[label]) == prep[label + '_files']
    for name, digest in prep['source_files'].items():
        assert sha256(ROOT / name) == digest, name
    for name in ['roots.jsonl', 'fixed-roots.jsonl', 'choice-cache.seed.jsonl']:
        assert sha256(OUT / name) == prep['inputs'][name]


def worker(label):
    path = OUT / (label + '.json')
    assert not path.exists(), 'Preserve every attempt'
    prep = json.loads((OUT / 'preparation.json').read_text())
    verify(prep)
    candidate = ROOT / prep[label]
    report = dict(status='initializing', pid=os.getpid(), label=label,
        candidate=prep[label], preparation_sha256=sha256(OUT / 'preparation.json'),
        fixed=[], clock=[])
    save_json(path, report)
    try:
        stop_check()
        sys.path.insert(0, str(candidate.resolve()))
        tick = time.perf_counter()
        import chess
        import numpy as np

        import agent

        report['init_seconds'] = time.perf_counter() - tick
        assert report['init_seconds'] <= 90
        driver = sys.modules['engine.compiled_driver']
        core, arrays, decode = driver.core, driver.arrays, driver.decode
        assert Path(core.__file__).resolve() == (candidate / 'engine/compiled_core.py').resolve()
        search = agent._search
        search.policy = None

        def restore(row):
            board = chess.Board(row['start_fen'])
            for move in row['history']:
                board.push_uci(move)
            assert board.fen() == row['fen'] and board.is_valid()
            return board

        def clear():
            for name in ['ttkey', 'ttcontext', 'ttdata', 'killers', 'history']:
                getattr(search, name).fill(0)

        def fixed(row, bonus_mode, depth=None, nodes=500000):
            stop_check()
            clear()
            board = restore(row)
            pieces, state = arrays(board)
            saved_pieces, saved_state = pieces.copy(), state.copy()
            moves = core.legal_moves(pieces, state)
            previous = int(moves[0])
            bonuses = np.zeros(len(moves), dtype=np.int64)
            if bonus_mode == 'signed':
                bonuses = np.array([(i % 7 - 3) * 10 for i in range(len(moves))], dtype=np.int64)
            hashes = np.zeros(800, dtype=np.uint64)
            replay, past = board.copy(stack=True), []
            for _ in range(min(board.halfmove_clock, len(board.move_stack)) + 1):
                p, s = arrays(replay)
                past.append(core.position_hash(p, s))
                if not replay.move_stack:
                    break
                replay.pop()
            past.reverse()
            hashes[:len(past)] = past
            control = np.array([0, 0, nodes], dtype=np.int64)
            tick = time.perf_counter()
            chosen, score, complete = core.root_iteration(pieces, state, depth or row['depth'],
                previous, moves, bonuses, hashes, len(past), search.ttkey, search.ttcontext,
                search.ttdata, search.killers, search.history, control, tick + 8,
                search.weights, search.bias, search.output, search.blend, search.conversion,
                search.reductions)
            elapsed = time.perf_counter() - tick
            assert np.array_equal(pieces, saved_pieces) and np.array_equal(state, saved_state)
            assert list(hashes[:len(past)]) == past
            assert int(control[0]) <= nodes and elapsed <= 8.25
            move = decode(int(chosen))
            assert move in board.legal_moves
            if not complete:
                assert int(chosen) == previous
            if row['id'] == 'mate-in-one' and complete:
                board.push(move)
                assert board.is_checkmate() and int(score) == 29999
            return dict(id=row['id'], mode=bonus_mode, depth=depth or row['depth'],
                complete=bool(complete), uci=move.uci(), score=int(score) if complete else None,
                nodes=int(control[0]), seconds=elapsed)

        fixed_rows = [json.loads(line) for line in (OUT / 'fixed-roots.jsonl').read_text().splitlines()]
        assert len(fixed_rows) == 11
        report['status'] = 'fixed-depth-and-restoration'
        save_json(path, report)
        for row in fixed_rows:
            for bonus_mode in ['zero', 'signed']:
                result = fixed(row, bonus_mode)
                report['fixed'].append(result)
                save_json(path, report)
                assert result['complete'], 'Fixed-depth resource cap; no score parity claim'
        interrupted = fixed(next(r for r in fixed_rows if r['id'] == 'initial'), 'signed', depth=12, nodes=512)
        report['interrupted'] = interrupted
        assert not interrupted['complete'] and interrupted['nodes'] == 512
        report['status'] = 'clock-probes'
        save_json(path, report)
        roots = [json.loads(line) for line in (OUT / 'roots.jsonl').read_text().splitlines()]
        assert len(roots) == len({r['id'] for r in roots}) == 21
        for row in roots:
            stop_check()
            board = restore(row)
            stack = list(board.move_stack)
            clear()
            tick = time.perf_counter()
            result = search.run(board, seconds=1., soft=1., max_depth=64)
            elapsed = time.perf_counter() - tick
            assert result.move in board.legal_moves and board.fen() == row['fen'] and board.move_stack == stack
            report['clock'].append(dict(id=row['id'], uci=result.move.uci(), depth=result.depth,
                score=result.score, nodes=result.nodes, seconds=result.elapsed, wall_seconds=elapsed,
                repeats_played=result.move.uci() == row['played']))
            save_json(path, report)
            assert result.depth >= 1 and elapsed <= 1.25
        verify(prep)
        report['status'] = 'complete'
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(path, report)
    print(json.dumps(dict(label=label, status=report['status'], init_seconds=report['init_seconds'],
        fixed=len(report['fixed']), clock=len(report['clock']))), flush=True)


def main():
    from scripts.improvement_king_coordination_gate import child
    from scripts.overnight_capacity import wait_for_capacity

    assert not (OUT / 'context.json').exists(), 'No unchanged pilot retries'
    prep = json.loads((OUT / 'preparation.json').read_text())
    verify(prep)
    assert sha256(OUT / 'choice-cache.jsonl') == prep['inputs']['choice-cache.seed.jsonl']
    state = dict(status='running', stage='independent-window-tests',
        preparation_sha256=sha256(OUT / 'preparation.json'))
    save_json(OUT / 'context.json', state)
    try:
        wait_for_capacity(OUT / 'tests-capacity.json')
        child(['-m', 'pytest', 'tests/test_root_pvs.py', '-q', '--junitxml', str(OUT / 'tests.xml')],
            OUT / 'tests.log', timeout=120)
        suite = ET.parse(OUT / 'tests.xml').getroot().find('testsuite')
        assert [int(suite.attrib[k]) for k in ['tests', 'failures', 'errors', 'skipped']] == [9, 0, 0, 0]
        reports = {}
        for label in ['baseline', 'prototype']:
            state['stage'] = label + '-fixed-and-clock'
            save_json(OUT / 'context.json', state)
            wait_for_capacity(OUT / (label + '-capacity.json'))
            child(['-m', 'scripts.root_pvs_pilot', '--worker', label], OUT / (label + '.log'), timeout=360)
            reports[label] = json.loads((OUT / (label + '.json')).read_text())
            assert reports[label]['status'] == 'complete'
        mismatches = []
        for a, b in zip(reports['baseline']['fixed'], reports['prototype']['fixed'], strict=True):
            assert (a['id'], a['mode'], a['depth']) == (b['id'], b['mode'], b['depth'])
            if a['score'] != b['score']:
                mismatches.append(dict(id=a['id'], mode=a['mode'], baseline=a['score'], prototype=b['score']))
        nodes = {label: sum(r['nodes'] for r in report['fixed']) for label, report in reports.items()}
        depths = {label: statistics.mean(r['depth'] for r in report['clock']) for label, report in reports.items()}
        reduction = 1 - nodes['prototype'] / nodes['baseline']
        cheap = not mismatches and reduction >= .10 and depths['prototype'] >= depths['baseline']
        passed, teacher = False, None
        if cheap:
            from training.mistake_replay import review_choices

            state['stage'] = 'bounded-teacher-review'
            save_json(OUT / 'context.json', state)
            roots = [json.loads(line) for line in (OUT / 'roots.jsonl').read_text().splitlines()]
            reviews = {}
            for label in ['baseline', 'prototype']:
                wait_for_capacity(OUT / (label + '-teacher-capacity.json'))
                reviews[label] = review_choices([dict(root=r) for r in roots], reports[label]['clock'],
                    OUT / 'choice-cache.jsonl')
                save_json(OUT / (label + '-review.json'), reviews[label])
            errors, mates, repairs = [], [], []
            for a, b in zip(reviews['baseline']['records'], reviews['prototype']['records'], strict=True):
                assert a['id'] == b['id']
                if max(a['regret']) < 200 and min(b['regret']) >= 200:
                    errors.append(a['id'])
                if b['mate_loss'] and not a['mate_loss']:
                    mates.append(a['id'])
                if a['id'].startswith('rated52:') and all(x - y >= 100 for x, y in zip(a['regret'], b['regret'], strict=True)):
                    repairs.append(a['id'])
            means = {label: review['mean_regret'] for label, review in reviews.items()}
            teacher = dict(mean_regret=means, new_errors=errors, new_mates=mates, recent_repairs=repairs,
                new_teacher_nodes=sum(v['new_teacher_nodes'] for v in reviews.values()))
            assert teacher['new_teacher_nodes'] <= 16800000
            passed = bool(not errors and not mates and repairs
                and all(b <= a for a, b in zip(means['baseline'], means['prototype'], strict=True)))
        verify(prep)
        gate = dict(status='complete', passed=passed, cheap_pass=bool(cheap), score_mismatches=mismatches,
            fixed_depth_nodes=nodes, node_reduction_fraction=reduction, mean_clock_depth=depths,
            teacher_review=teacher, automatic_promotion=False, games=0, fitting_updates=0)
        save_json(OUT / 'gate.json', gate)
        state.update(status='complete', stage='awaiting_critique', passed=passed)
        print(json.dumps(gate), flush=True)
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(OUT / 'context.json', state)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--worker', choices=['baseline', 'prototype'])
    args = parser.parse_args()
    if args.worker:
        worker(args.worker)
    else:
        main()
