"""Bounded quiescence-result cache experiment; frozen53 remains the baseline."""

import argparse
import ast
import json
import os
import queue
import shutil
import statistics
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from scripts import overnight_hash_scout_fixed as runner
from scripts.overnight_geometry_trial import BASE, ROOT, check_stop, digest, manifest, save

OUT = ROOT / 'runs/overnight-20260909/qcache-01'

HELPERS = '''
@njit(cache=False)
def qcache_context(context, depth, qdepth):
    return (context ^ (np.uint64(qdepth + 1) * np.uint64(0xa24baed4963ee407))
            ^ (np.uint64(depth + 128) * np.uint64(0x9fb21c651e98df25)))


@njit(cache=False)
def qcache_probe(key, context, clock, ply, alpha, beta, ttkey, ttcontext, ttdata):
    slot = int(key & np.uint64(len(ttkey) - 1))
    if (ttkey[slot] == key and ttcontext[slot] == context
            and ttdata[slot, 0] == -1000 and ttdata[slot, 4] == clock):
        value = ttdata[slot, 1]
        value = value - ply if value > 29000 else value + ply if value < -29000 else value
        bound = ttdata[slot, 2]
        if bound == 0 or (bound == 1 and value >= beta) or (bound == 2 and value <= alpha):
            return True, value
    return False, 0


@njit(cache=False)
def qcache_store(key, context, clock, ply, value, move, alpha, beta, ttkey, ttcontext, ttdata):
    slot = int(key & np.uint64(len(ttkey) - 1))
    # Normal-depth results retain their slots; normal search can replace these.
    if ttkey[slot] != 0 and ttdata[slot, 0] >= 0:
        return
    packed = value + ply if value > 29000 else value - ply if value < -29000 else value
    ttkey[slot], ttcontext[slot] = key, context
    ttdata[slot, 0], ttdata[slot, 1] = -1000, packed
    ttdata[slot, 2] = 2 if value <= alpha else 1 if value >= beta else 0
    ttdata[slot, 3], ttdata[slot, 4] = move, clock


'''


def changed_source(original):
    marker = '@njit(cache=False)\ndef search('
    start = original.index(marker)
    source = original[:start] + HELPERS + original[start:]
    old = '    original_alpha = alpha\n'
    new = old + '''    qcontext = qcache_context(tt_context, depth, qdepth)
    if quiescence:
        found, cached = qcache_probe(key, qcontext, state[3], ply, alpha, beta,
                                     ttkey, ttcontext, ttdata)
        if found:
            return cached
'''
    assert source.count(old) == 1
    source = source.replace(old, new)
    old = '        if qdepth >= 12 or stand >= beta:\n            return stand\n'
    new = '''        if qdepth >= 12 or stand >= beta:
            qcache_store(key, qcontext, state[3], ply, stand, 0, original_alpha, beta,
                         ttkey, ttcontext, ttdata)
            return stand
'''
    assert source.count(old) == 1
    source = source.replace(old, new)
    old = '        ttdata[slot, 3], ttdata[slot, 4] = bestmove, state[3]\n    return best\n'
    new = '''        ttdata[slot, 3], ttdata[slot, 4] = bestmove, state[3]
    else:
        qcache_store(key, qcontext, state[3], ply, best, bestmove, original_alpha, beta,
                     ttkey, ttcontext, ttdata)
    return best
'''
    assert source.count(old) == 1
    source = source.replace(old, new)
    allowed = {'search', 'qcache_context', 'qcache_probe', 'qcache_store'}
    def unchanged(text):
        return [ast.dump(n) for n in ast.parse(text).body
                if not (isinstance(n, ast.FunctionDef) and n.name in allowed)]
    assert unchanged(source) == unchanged(original)
    return source


def prepare():
    assert not OUT.exists(), 'Preserve completed and partial preparations'
    OUT.mkdir(parents=True)
    source = changed_source((BASE / 'engine/compiled_core.py').read_text(encoding='utf-8'))
    prototype = OUT / 'prototype'
    shutil.copytree(BASE, prototype, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    (prototype / 'engine/compiled_core.py').write_text(source, encoding='utf-8', newline='\n')
    experiment = ROOT / 'experiments/overnight_qcache_core.py'
    assert not experiment.exists()
    experiment.write_text(source, encoding='utf-8', newline='\n')
    earlier = ROOT / 'runs/overnight-20260909/budgeted-checks-01/preparation.json'
    roots = json.loads(earlier.read_text(encoding='utf-8'))['roots']
    reviews = sorted((OUT.parent / 'field-01/review/games').glob('*/review.json'))
    wanted = {"Istanbul's finest": [14, 26, 31, 34], 'CCC': [26], 'Alpha Knights': [30]}
    for path in reviews:
        doc = json.loads(path.read_text(encoding='utf-8'))
        assert doc['status'] == 'complete'
        opponent = doc['identity']['game']['opponent']
        for number in wanted[opponent]:
            row = next(r for r in doc['rows'] if r['fullmove'] == number)
            roots.append(dict(id=f'field-{opponent}-move-{number}',
                start_fen=row['start_fen'], history=row['history'], fen=row['fen'],
                actual_played=row['played'], source_game_id=doc['identity']['game']['source_game_id']))
    assert len(roots) == len({r['id'] for r in roots}) == 22
    save(OUT / 'preparation.json', dict(created_utc=datetime.now(timezone.utc).isoformat(),
        candidates={'baseline': str(BASE.relative_to(ROOT)), 'prototype': str(prototype.relative_to(ROOT))},
        candidate_files={'baseline': manifest(BASE), 'prototype': manifest(prototype)}, roots=roots,
        source_sha256={str(p.relative_to(ROOT)): digest(p) for p in [Path(__file__),
            ROOT / 'scripts/overnight_hash_scout_fixed.py', ROOT / 'scripts/overnight_geometry_trial.py',
            ROOT / 'tests/test_overnight_qcache.py', ROOT / 'docs/OVERNIGHT_QCACHE_PLAN_20260909.md',
            earlier, experiment, *reviews]},
        fixed_depth=2, per_root_order='ABBA', minimum_aggregate_cpu_speedup=1.10,
        scope='22 exposed development roots, fixed score equivalence and clock quality; no Elo.'))


def worker(label):
    prep = json.loads((OUT / 'preparation.json').read_text(encoding='utf-8'))
    candidate = ROOT / prep['candidates'][label]
    sys.path.insert(0, str(candidate))
    tick = time.perf_counter()
    import chess

    import agent

    init = time.perf_counter() - tick
    assert Path(sys.modules['engine.compiled_core'].__file__).resolve() == candidate / 'engine/compiled_core.py'
    print(json.dumps(dict(status='ready', init_seconds=init)), flush=True)
    for line in sys.stdin:
        request = json.loads(line)
        if request.get('stop'):
            return
        root = prep['roots'][request['root']]
        check_stop()
        board = chess.Board(root['start_fen'])
        for uci in root['history']:
            board.push_uci(uci)
        assert board.fen() == root['fen']
        history = board.move_stack.copy()
        for key in ('ttkey', 'ttcontext', 'ttdata', 'killers', 'history'):
            getattr(agent._search, key).fill(0)
        fixed = request['regime'] == 'fixed'
        seconds = 12. if fixed else 1.
        tick = time.process_time()
        result = agent._search.run(board, seconds, seconds, max_depth=2 if fixed else 64,
                                   max_nodes=2000000 if fixed else 2**60)
        cpu = time.process_time() - tick
        assert result.move in board.legal_moves
        assert board.fen() == root['fen'] and board.move_stack == history
        assert result.elapsed <= seconds + .3
        print(json.dumps(dict(**request, id=root['id'], label=label, uci=result.move.uci(),
            score=result.score, depth=result.depth, nodes=result.nodes,
            seconds=result.elapsed, cpu_seconds=cpu)), flush=True)


class WarmWorker(runner.WarmWorker):
    def __init__(self, label):
        self.label = label
        self.log = (OUT / f'{label}.log').open('w', encoding='utf-8')
        self.answers = queue.Queue()
        self.process = subprocess.Popen([sys.executable, '-X', 'utf8', '-m',
            'scripts.overnight_qcache', '--worker', label], cwd=ROOT,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.log,
            text=True, encoding='utf-8',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        def read():
            for line in self.process.stdout:
                self.answers.put(line)
            self.answers.put(None)
        threading.Thread(target=read, daemon=True).start()


def controller():
    from scripts.overnight_capacity import wait_for_capacity

    prep = json.loads((OUT / 'preparation.json').read_text(encoding='utf-8'))
    suite = ET.parse(OUT / 'tests.xml').getroot().find('testsuite')
    assert int(suite.attrib['tests']) >= 10
    assert all(int(suite.attrib[k]) == 0 for k in ('errors', 'failures', 'skipped'))
    assert not (OUT / 'state.json').exists()
    report, workers = dict(status='running', passed=False, workers={}, rows=[]), {}
    save(OUT / 'state.json', report)
    try:
        for path, expected in prep['source_sha256'].items():
            assert digest(ROOT / path) == expected
        for label in ('baseline', 'prototype'):
            check_stop()
            wait_for_capacity(OUT / f'{label}-capacity.json', minimum_memory_mb=1400, wait_seconds=120)
            workers[label] = WarmWorker(label)
            report['workers'][label] = dict(pid=workers[label].process.pid, status='initializing')
            save(OUT / 'state.json', report)
            ready = workers[label].receive(90)
            report['workers'][label].update(ready)
            save(OUT / 'state.json', report)
            assert ready['init_seconds'] < 90
        for index in range(len(prep['roots'])):
            for regime in ('fixed', 'clock'):
                for block, label in enumerate(('baseline', 'prototype', 'prototype', 'baseline')):
                    check_stop()
                    row = workers[label].ask(dict(root=index, regime=regime, block=block))
                    report['rows'].append(row)
                    save(OUT / 'state.json', report)
        fixed = [r for r in report['rows'] if r['regime'] == 'fixed']
        completed = all(r['depth'] == 2 or abs(r['score']) > 29900 for r in fixed)
        parity = all(len({(r['score'], r['depth']) for r in fixed if r['root'] == i}) == 1
                     for i in range(len(prep['roots'])))
        totals = {label: sum(r['cpu_seconds'] for r in fixed if r['label'] == label) for label in workers}
        depths = {label: statistics.mean(r['depth'] for r in report['rows']
                  if r['regime'] == 'clock' and r['label'] == label) for label in workers}
        ratios = [sum(r['cpu_seconds'] for r in fixed if r['root'] == i and r['label'] == 'baseline') /
                  max(1e-9, sum(r['cpu_seconds'] for r in fixed if r['root'] == i and r['label'] == 'prototype'))
                  for i in range(len(prep['roots']))]
        speedup = totals['baseline'] / max(1e-9, totals['prototype'])
        report.update(status='complete', fixed_completed=completed, fixed_score_parity=parity,
            fixed_cpu_totals=totals, aggregate_cpu_speedup=speedup, per_root_cpu_ratios=ratios,
            median_cpu_speedup=statistics.median(ratios), clock_mean_depth=depths,
            passed=bool(completed and parity and speedup >= 1.10 and depths['prototype'] >= depths['baseline']))
        report['decision'] = 'needs_teacher_review_then_readonly_and_short_matches' if report['passed'] else 'reject_efficiency_gate'
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        for process in workers.values():
            process.close()
        report['completed_utc'] = datetime.now(timezone.utc).isoformat()
        report['frozen_candidates'] = all(manifest(ROOT / path) == prep['candidate_files'][label]
                                          for label, path in prep['candidates'].items())
        if not report['frozen_candidates']:
            report.update(status='failed', passed=False, error='Frozen candidate mutated')
        save(OUT / 'state.json', report)
        print(json.dumps({k: v for k, v in report.items() if k != 'rows'}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--worker', choices=('baseline', 'prototype'))
    args = parser.parse_args()
    if args.prepare:
        prepare()
    elif args.worker:
        worker(args.worker)
    else:
        controller()
