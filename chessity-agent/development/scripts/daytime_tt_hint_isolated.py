"""History-safe move hints on the frozen faster parent, with warm ABBA timing."""

import argparse
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

from scripts.daytime_common import ROOT, RUN, check_stop, digest, manifest, save

OUT = RUN / 'tt-hint-02'
BASE = RUN / 'fast-legal-01/prototype'

from scripts.daytime_tt_hint_transform import transform


def prepare():
    check_stop()
    assert not OUT.exists()
    previous=RUN/'field-selected-probe-supervisor-01/supervisor.json'
    assert json.loads(previous.read_text())['status']=='complete'
    probe=RUN/'field-selected-probe-01/diagnosis.json'
    assert json.loads(probe.read_text())['status']=='complete'
    parent_prep=RUN/'fast-legal-01/preparation.json'
    old=json.loads(parent_prep.read_text())
    assert manifest(BASE)==old['candidate_files']['prototype']
    prototype=OUT/'prototype'
    shutil.copytree(BASE,prototype,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    changed=transform((BASE/'engine/compiled_core.py').read_text())
    (prototype/'engine/compiled_core.py').write_text(changed,encoding='utf-8',newline='\n')
    experiment=ROOT/'experiments/daytime_tt_hint_core.py'
    assert experiment.read_text()==changed, 'Preserve exactly the first prototype source'
    public_prep=RUN/'field-selected-probe-01/preparation.json'
    progress=RUN/'fast-legal-progress-02/diagnosis.json'
    roots=old['roots'][:]
    roots += [{k:r[k] for k in ('id','start_fen','history','fen')}
        for r in json.loads(public_prep.read_text())['roots']]
    targets=json.loads(progress.read_text())['targets']
    for white,fullmove in ((True,15),(False,25)):
        rows=[r for r in targets if r['match']=='versus55' and r['candidate_white']==white
            and r['fullmove']==fullmove]
        assert len(rows)==1
        roots.append(dict(id=f'fast-versus55-{white}-{fullmove}',
            **{k:rows[0][k] for k in ('start_fen','history','fen')}))
    assert len(roots)==19 and len({r['fen'] for r in roots})==19
    paths=[Path(__file__),ROOT/'scripts/daytime_tt_hint_transform.py',
        ROOT/'scripts/daytime_common.py',ROOT/'tests/test_daytime_tt_hint_isolated.py',
        ROOT/'docs/DAYTIME_TT_HINT_PLAN_20260909.md',
        ROOT/'docs/DAYTIME_TT_HINT_ISOLATION_20260909.md',
        ROOT/'scripts/daytime_tt_hint_reference.py',ROOT/'scripts/daytime_tt_hint_test_call.py',experiment,previous,probe,
        parent_prep,public_prep,progress]
    save(OUT/'preparation.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        candidates={'baseline':str(BASE.relative_to(ROOT)),'prototype':str(prototype.relative_to(ROOT))},
        candidate_files={'baseline':manifest(BASE),'prototype':manifest(prototype)},roots=roots,
        source_sha256={str(p.relative_to(ROOT)):digest(p) for p in paths},
        protocol=dict(fixed_depth=6,fixed_reductions=False,max_nodes=5000000,
            fixed_seconds_cap=12,clock_seconds=1,clock_reductions=True,
            order=['baseline','prototype','prototype','baseline'],minimum_cpu_ratio=1.05,
            minimum_timed_roots=8,minimum_baseline_cpu_seconds=.05,minimum_baseline_nodes=10000),
        scope='Ordering hints only across foreign history; cached score guards unchanged. Exposed development roots.'))
    print('Prepared 19-root history-safe hint trial',flush=True)


def worker(label):
    prep = json.loads((OUT / 'preparation.json').read_text(encoding='utf-8'))
    candidate = ROOT / prep['candidates'][label]
    sys.path.insert(0, str(candidate))
    # Production agent establishes Numba/platform settings before any engine import.
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
        row = prep['roots'][request['root']]
        check_stop()
        board = chess.Board(row['start_fen'])
        for move in row['history']:
            board.push_uci(move)
        assert board.fen() == row['fen']
        history = board.move_stack.copy()
        for key in ('ttkey', 'ttcontext', 'ttdata', 'killers', 'history'):
            getattr(agent._search, key).fill(0)
        fixed = request['regime'] == 'fixed'
        seconds = 12. if fixed else 1.
        cpu = time.process_time()
        agent._search.reductions = not fixed
        result = agent._search.run(board, seconds, seconds, max_depth=6 if fixed else 64,
                                   max_nodes=5000000)
        cpu = time.process_time() - cpu
        assert result.move in board.legal_moves
        assert board.fen() == row['fen'] and board.move_stack == history
        assert result.elapsed <= seconds + .3
        print(json.dumps(dict(**request, id=row['id'], label=label, uci=result.move.uci(),
            score=result.score, depth=result.depth, nodes=result.nodes, seconds=result.elapsed,
            cpu_seconds=cpu)), flush=True)


class WarmWorker:
    def __init__(self, label):
        self.label = label
        self.log = (OUT / f'{label}.log').open('w', encoding='utf-8')
        self.answers = queue.Queue()
        self.process = subprocess.Popen([sys.executable, '-X', 'utf8', '-m', 'scripts.daytime_tt_hint_isolated',
            '--worker', label], cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=self.log, text=True, encoding='utf-8',
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        def read():
            for line in self.process.stdout:
                self.answers.put(line)
            self.answers.put(None)
        threading.Thread(target=read, daemon=True).start()

    def receive(self, timeout):
        try:
            line = self.answers.get(timeout=timeout)
        except queue.Empty:
            raise TimeoutError(f'{self.label} exceeded {timeout}s response watchdog') from None
        if line is None:
            raise RuntimeError(f'{self.label} exited; inspect preserved log')
        return json.loads(line)

    def ask(self, request):
        self.process.stdin.write(json.dumps(request) + '\n')
        self.process.stdin.flush()
        return self.receive(15)

    def close(self):
        if self.process.poll() is None:
            try:
                self.process.stdin.write('{"stop":true}\n')
                self.process.stdin.flush()
                self.process.wait(timeout=3)
            except (OSError, subprocess.TimeoutExpired):
                self.process.kill()
                self.process.wait()
        self.log.close()


def controller():
    from scripts.overnight_capacity import wait_for_capacity

    prep = json.loads((OUT / 'preparation.json').read_text(encoding='utf-8'))
    suite = ET.parse(OUT / 'tests.xml').getroot().find('testsuite')
    assert int(suite.attrib['tests']) >= 10
    assert all(int(suite.attrib[k]) == 0 for k in ('errors', 'failures', 'skipped'))
    report = dict(status='running', passed=False, workers={}, rows=[])
    assert not (OUT / 'state.json').exists()
    save(OUT / 'state.json', report)
    workers = {}
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
        # Both workers stay resident; only one executes a search at a time.
        # ABBA per-root order balances short-term load/frequency drift without re-JIT.
        for index in range(len(prep['roots'])):
            for regime in ('fixed', 'clock'):
                for block, label in enumerate(('baseline', 'prototype', 'prototype', 'baseline')):
                    check_stop()
                    row = workers[label].ask(dict(root=index, regime=regime, block=block))
                    report['rows'].append(row)
                    save(OUT / 'state.json', report)
        fixed = [r for r in report['rows'] if r['regime'] == 'fixed']
        completed = all(r['depth'] == 6 or abs(r['score']) > 29900 for r in fixed)
        parity, ratios, node_ratios, timed = True, [], [], []
        for index in range(len(prep['roots'])):
            rows = [r for r in fixed if r['root'] == index]
            parity &= len({r['score'] for r in rows}) == 1
            a = [r for r in rows if r['label'] == 'baseline']
            b = [r for r in rows if r['label'] == 'prototype']
            if statistics.mean(r['cpu_seconds'] for r in a) >= .05 and statistics.mean(r['nodes'] for r in a) >= 10000:
                timed += rows
                ratios.append(statistics.mean(r['cpu_seconds'] for r in a) /
                              max(1e-9, statistics.mean(r['cpu_seconds'] for r in b)))
                node_ratios.append(statistics.mean(r['nodes'] for r in b) / statistics.mean(r['nodes'] for r in a))
        depths = {label: statistics.mean(r['depth'] for r in report['rows']
                  if r['regime'] == 'clock' and r['label'] == label) for label in workers}
        aggregate_ratio = sum(r['cpu_seconds'] for r in timed if r['label'] == 'baseline') / max(1e-9, sum(r['cpu_seconds'] for r in timed if r['label'] == 'prototype'))
        report.update(aggregate_cpu_speedup=aggregate_ratio, fixed_completed=completed, fixed_score_parity=parity, timed_roots=len(ratios),
            median_cpu_speedup=statistics.median(ratios) if ratios else 0.0, cpu_ratios=ratios,
            median_node_ratio=statistics.median(node_ratios) if node_ratios else 0.0, clock_mean_depth=depths)
        report['passed'] = bool(completed and parity and len(ratios) >= 8 and statistics.median(ratios) >= 1.05 and aggregate_ratio >= 1.05
                               and depths['prototype'] >= depths['baseline'])
        report.update(status='complete', decision='needs_teacher_review_and_short_matches'
                      if report['passed'] else 'reject_efficiency_gate')
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        for worker_process in workers.values():
            worker_process.close()
        report['completed_utc'] = datetime.now(timezone.utc).isoformat()
        report['frozen_candidates'] = all(manifest(ROOT / path) == prep['candidate_files'][label]
                                          for label, path in prep['candidates'].items())
        if not report['frozen_candidates']:
            report.update(status='failed', passed=False, error='Candidate mutated')
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
