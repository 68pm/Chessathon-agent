"""One bounded exact-evaluation geometry experiment on frozen v1.53."""

import argparse
import hashlib
import json
import os
import random
import shutil
import statistics
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/overnight-20260909/geometry-01'
BASE = ROOT / 'candidates/compiled-near-queen-checks-v1'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(path):
    return {p.relative_to(path).as_posix(): digest(p) for p in sorted(path.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def check_stop():
    if any(p.exists() for p in (ROOT / 'STOP_TRAINING', ROOT / 'STOP_BENCHMARK',
                                OUT.parent / 'STOP')):
        raise InterruptedError('User stop flag')
    if datetime.now(timezone.utc) >= datetime(2026, 9, 9, 5, 40, tzinfo=timezone.utc):
        raise InterruptedError('Overnight heavy-work deadline reached')


def geometry_source(source):
    # Constants reproduce the original arithmetic exactly, including king/pawn terms.
    tables = '''
BASE_MG = np.zeros((7, 128), dtype=np.int64)
BASE_EG = np.zeros((7, 128), dtype=np.int64)
KING_RING = np.zeros((128, 128), dtype=np.uint8)
for _sq in range(128):
    if _sq & 0x88:
        continue
    _f, _r = _sq % 16, _sq // 16
    _center = 7 - abs(2 * _f - 7) - abs(2 * _r - 7)
    for _p in range(1, 7):
        if _p == 1:
            _a, _b = 6 * _r + 2 * _center, 10 * _r + _center
        elif _p == 2:
            _a, _b = 7 * _center, 5 * _center
        elif _p == 3:
            _a, _b = 4 * _center + 2 * _r, 4 * _center
        elif _p == 4:
            _a, _b = 2 * _r + (15 if _r == 6 else 0), 2 * _center
        elif _p == 5:
            _a, _b = _center - max(0, _r - 2) * 2, 3 * _center
        else:
            _a = -5 * _center - 8 * _r + (22 if _r == 0 and _f in (1, 2, 6) else 0)
            _b = 7 * _center
        BASE_MG[_p, _sq], BASE_EG[_p, _sq] = MG[_p] + _a, EG[_p] + _b
    for _target in range(128):
        if not _target & 0x88:
            KING_RING[_sq, _target] = int(max(abs(_f - _target % 16),
                                                   abs(_r - _target // 16)) == 1)

'''
    location = source.index('@njit(cache=False)')
    source = source[:location] + tables + source[location:]
    start = source.index('        center = 7 - abs(2 * f - 7) - abs(2 * r - 7)', source.index('def classical('))
    end = source.index('        if p == 1:\n            if pawns[c, f] > 1:', start)
    source = source[:start] + ('        relative = r * 16 + f\n'
        '        a, b = BASE_MG[p, relative], BASE_EG[p, relative]\n') + source[end:]
    old = 'pressure += int(max(abs(target % 16 - ek % 16), abs(target // 16 - ek // 16)) == 1)'
    assert source.count(old) == 1
    source = source.replace(old, 'pressure += KING_RING[ek, target]')
    return source


def prepare():
    import chess

    assert not OUT.exists(), 'Single-use trial; preserve existing output'
    OUT.mkdir(parents=True)
    prototype = OUT / 'prototype'
    shutil.copytree(BASE, prototype, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    source = geometry_source((BASE / 'engine/compiled_core.py').read_text(encoding='utf-8'))
    (prototype / 'engine/compiled_core.py').write_text(source, encoding='utf-8', newline='\n')
    before, after = manifest(BASE), manifest(prototype)
    assert before.keys() == after.keys()
    assert [k for k in before if before[k] != after[k]] == ['engine/compiled_core.py']
    prior = ROOT / 'runs/all-game-feedback-20260908/pilot/preparation.json'
    roots = json.loads(prior.read_text(encoding='utf-8'))['roots']
    # Freeze a deterministic mixed corpus before measuring either implementation.
    rng, fens = random.Random(202609092220), []
    for _ in range(16):
        board = chess.Board()
        for ply in range(180):
            if board.is_game_over():
                break
            board.push(rng.choice(list(board.legal_moves)))
            if ply % 5 == 0:
                fens.append(board.fen())
    for row in roots:
        fens.append(row['fen'])
    fens.extend(['8/8/8/8/8/3k4/8/KR6 w - - 0 1',
                 '8/8/8/8/8/3k4/8/KB6 w - - 0 1',
                 '8/8/8/8/8/3k4/8/KN6 w - - 0 1',
                 '8/8/8/8/8/3k4/8/KQ6 w - - 0 1'])
    fens = list(dict.fromkeys(fens))
    save(OUT / 'preparation.json', dict(
        created_utc=datetime.now(timezone.utc).isoformat(),
        candidates={'baseline': str(BASE.relative_to(ROOT)), 'prototype': str(prototype.relative_to(ROOT))},
        candidate_files={'baseline': before, 'prototype': after},
        source_sha256={str(Path(__file__).relative_to(ROOT)): digest(Path(__file__)),
                       str(prior.relative_to(ROOT)): digest(prior)},
        roots=roots[:8], evaluation_fens=fens, search_nodes=250000,
        scope='New exact evaluator geometry on53; exposed-root speed diagnostic, not Elo.'))
    print(json.dumps({'prepared': str(OUT), 'evaluation_positions': len(fens), 'roots': 8}), flush=True)


def worker(mode, label, block):
    prep = json.loads((OUT / 'preparation.json').read_text(encoding='utf-8'))
    candidate = ROOT / prep['candidates'][label]
    path = OUT / f'{mode}-{block}-{label}.json'
    assert not path.exists()
    sys.path.insert(0, str(candidate))
    import chess
    import numpy as np
    from engine.compiled_driver import arrays
    from numba import njit

    from engine import compiled_core as core

    assert Path(core.__file__).resolve() == candidate / 'engine/compiled_core.py'
    state = dict(status='running', label=label, block=block, mode=mode, rows=[])
    save(path, state)
    try:
        if mode == 'eval':
            entries = [arrays(chess.Board(fen)) for fen in prep['evaluation_fens']]
            boards = np.stack([b for b, _ in entries])
            states = np.stack([s for _, s in entries])

            @njit(cache=False)
            def batch(boards, states, repeats):
                checksum = 0
                for _ in range(repeats):
                    for i in range(len(boards)):
                        checksum += core.classical(boards[i], states[i], False)
                return checksum

            batch(boards, states, 1)
            # Conversion-off AND conversion-on equivalence is checked separately.
            state['values'] = [[int(core.classical(b, s, flag)) for flag in (False, True)]
                               for b, s in entries]
            cpu, wall = time.process_time(), time.perf_counter()
            checksum = batch(boards, states, 512)
            state.update(cpu_seconds=time.process_time() - cpu, seconds=time.perf_counter() - wall,
                         checksum=int(checksum), calls=512 * len(entries))
        else:
            started = time.perf_counter()
            import agent

            state['init_seconds'] = time.perf_counter() - started
            assert state['init_seconds'] < 90
            for row in prep['roots']:
                for regime in ('fixed', 'clock'):
                    check_stop()
                    board = chess.Board(row['start_fen'])
                    for move in row['history']:
                        board.push_uci(move)
                    assert board.fen() == row['fen']
                    history = board.move_stack.copy()
                    for key in ('ttkey', 'ttcontext', 'ttdata', 'killers', 'history'):
                        getattr(agent._search, key).fill(0)
                    # Existing policy stays enabled in both builds.
                    limit = prep['search_nodes'] if regime == 'fixed' else 2**60
                    seconds = 15. if regime == 'fixed' else 1.
                    cpu = time.process_time()
                    result = agent._search.run(board, seconds, seconds, max_nodes=limit)
                    elapsed_cpu = time.process_time() - cpu
                    state['rows'].append(dict(id=row['id'], regime=regime, uci=result.move.uci(),
                        score=result.score, depth=result.depth, nodes=result.nodes,
                        seconds=result.elapsed, cpu_seconds=elapsed_cpu))
                    save(path, state)
                    assert result.move in board.legal_moves
                    assert board.fen() == row['fen'] and board.move_stack == history
                    assert result.elapsed < seconds + .3
        state['status'] = 'complete'
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        save(path, state)


def run_child(mode, label, block):
    from scripts.overnight_capacity import wait_for_capacity

    check_stop()
    wait_for_capacity(OUT / f'{mode}-{block}-{label}-capacity.json', minimum_memory_mb=1400,
                      wait_seconds=120)
    with (OUT / f'{mode}-{block}-{label}.log').open('w', encoding='utf-8') as log:
        child = subprocess.Popen([sys.executable, '-X', 'utf8', str(Path(__file__).resolve()),
            '--worker', mode, '--label', label, '--block', str(block)], cwd=ROOT,
            stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        save(OUT / 'active-child.json', dict(pid=child.pid, mode=mode, label=label, block=block))
        try:
            code = child.wait(timeout=100 if mode == 'eval' else 250)
        except subprocess.TimeoutExpired:
            child.kill()
            child.wait()
            raise RuntimeError(f'{mode}/{label} exceeded process budget') from None
    assert code == 0, f'{mode}/{label} failed; preserve output'
    return json.loads((OUT / f'{mode}-{block}-{label}.json').read_text(encoding='utf-8'))


def controller():
    prep = json.loads((OUT / 'preparation.json').read_text(encoding='utf-8'))
    report = dict(status='running', phase='evaluation', passed=False)
    save(OUT / 'state.json', report)
    try:
        assert all(digest(ROOT / p) == h for p, h in prep['source_sha256'].items())
        evaluations = [run_child('eval', label, i) for i, label in enumerate(
            ('baseline', 'prototype', 'prototype', 'baseline'))]
        assert all(r['values'] == evaluations[0]['values'] for r in evaluations)
        assert all(r['checksum'] == evaluations[0]['checksum'] for r in evaluations)
        cpu = {label: statistics.mean(r['cpu_seconds'] for r in evaluations if r['label'] == label)
               for label in ('baseline', 'prototype')}
        report.update(evaluation_parity=True, evaluation_cpu_ratio=cpu['baseline'] / cpu['prototype'])
        save(OUT / 'state.json', report)
        if report['evaluation_cpu_ratio'] < 1.10:
            report.update(status='complete', decision='reject_evaluator_speed_below_10_percent')
            return
        report['phase'] = 'equal_work_search'
        save(OUT / 'state.json', report)
        probes = [run_child('search', label, i) for i, label in enumerate(
            ('baseline', 'prototype', 'prototype', 'baseline'))]
        fixed = [[r for r in p['rows'] if r['regime'] == 'fixed'] for p in probes]
        def identity(row):
            return tuple(row[k] for k in ('id', 'uci', 'score', 'depth', 'nodes'))
        parity = all([identity(r) for r in rows] == [identity(r) for r in fixed[0]] for rows in fixed)
        reached = all(r['nodes'] >= prep['search_nodes'] or abs(r['score']) > 29900
                      for rows in fixed for r in rows)
        ratios = []
        for i in range(len(prep['roots'])):
            a = statistics.mean(fixed[j][i]['cpu_seconds'] for j in (0, 3))
            b = statistics.mean(fixed[j][i]['cpu_seconds'] for j in (1, 2))
            ratios.append(a / b)
        clock_depth = {label: statistics.mean(r['depth'] for p in probes if p['label'] == label
                       for r in p['rows'] if r['regime'] == 'clock') for label in ('baseline', 'prototype')}
        report.update(fixed_exact_parity=parity, fixed_budget_reached=reached,
            search_median_cpu_speedup=statistics.median(ratios), search_cpu_ratios=ratios,
            clock_mean_depth=clock_depth)
        report['passed'] = bool(parity and reached and statistics.median(ratios) >= 1.05
                               and clock_depth['prototype'] >= clock_depth['baseline'])
        report.update(status='complete', decision='needs_teacher_clock_review_and_small_match'
                      if report['passed'] else 'reject_search_gate')
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        report['completed_utc'] = datetime.now(timezone.utc).isoformat()
        report['frozen_candidates'] = all(manifest(ROOT / path) == prep['candidate_files'][label]
                                          for label, path in prep['candidates'].items())
        if not report['frozen_candidates']:
            report.update(status='failed', passed=False, error='Candidate changed during trial')
        save(OUT / 'state.json', report)
        print(json.dumps(report), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--worker', choices=('eval', 'search'))
    parser.add_argument('--label', choices=('baseline', 'prototype'))
    parser.add_argument('--block', type=int, default=0)
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.worker:
        worker(args.worker, args.label, args.block)
    else:
        controller()
