"""Bounded immediate queen mate proof on the preserved faster parent."""

import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

from scripts.daytime_common import ROOT, RUN, check_stop, digest, manifest, save

OUT = RUN/'contact-allq-02'
BASE = RUN/'fast-legal-01/prototype'

from scripts.daytime_contact_allq_transform import transform


def prepare():
    check_stop()
    assert not OUT.exists()
    parent_supervisor=RUN/'contact-mate-quality-supervisor-01/supervisor.json'
    assert json.loads(parent_supervisor.read_text())['status']=='complete'
    old_prep=RUN/'fast-legal-01/preparation.json'
    assert manifest(BASE)==json.loads(old_prep.read_text())['candidate_files']['prototype']
    prototype=OUT/'prototype'
    shutil.copytree(BASE,prototype,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    changed=transform((BASE/'engine/compiled_core.py').read_text())
    (prototype/'engine/compiled_core.py').write_text(changed,encoding='utf-8',newline='\n')
    experiment=ROOT/'experiments/daytime_contact_allq_core.py'
    assert not experiment.exists()
    experiment.write_text(changed,encoding='utf-8',newline='\n')
    previous=RUN/'tt-hint-02/preparation.json'
    roots=json.loads(previous.read_text())['roots'][:]
    labels_path=RUN/'student-descendants-02/teacher.json'
    labels=json.loads(labels_path.read_text())
    assert labels['status']=='complete'
    for number in (10,11):
        leaves=[r for r in labels['rows'] if r['root_id'].endswith('-'+str(number))
            and any(o['kind']=='student-endpoint' and o['branch']=='defence' for o in r['origins'])]
        assert len(leaves)==1 and all(t['mate']==1 for t in leaves[0]['teacher'])
        roots.append(dict(id=f'leaf-quiet-mate-{number}',
            **{k:leaves[0][k] for k in ('start_fen','history','fen')}))
    assert len(roots)==21 and len({r['fen'] for r in roots})==21
    public=json.loads((RUN/'field-selected-probe-01/preparation.json').read_text())
    sacrifices={r['id']:r['policy_target'] for r in public['roots'] if
        r['id'].startswith('own-') and r['id'].endswith(('-10','-11'))}
    assert len(sacrifices)==2
    paths=[Path(__file__),ROOT/'scripts/daytime_contact_allq_transform.py',
        ROOT/'scripts/daytime_contact_allq_quality.py',ROOT/'scripts/daytime_common.py',
        ROOT/'tests/test_daytime_contact_allq.py',ROOT/'scripts/daytime_contact_allq_test_call.py',
        ROOT/'docs/DAYTIME_CONTACT_ALLQ_PLAN_20260909.md',experiment,parent_supervisor,
        old_prep,previous,labels_path,RUN/'field-selected-probe-01/preparation.json']
    save(OUT/'preparation.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        candidates={'baseline':str(BASE.relative_to(ROOT)),'prototype':str(prototype.relative_to(ROOT))},
        candidate_files={'baseline':manifest(BASE),'prototype':manifest(prototype)},roots=roots,
        sacrifice_roots=sacrifices,source_sha256={str(p.relative_to(ROOT)):digest(p) for p in paths},
        protocol=dict(seconds=[1,3],max_nodes=5000000,order=['baseline','prototype','prototype','baseline']),
        scope='Immediate proven quiet contact mates at every nonchecked quiescence node. Exposed tactical diagnostics; playing files frozen.'))
    print('Prepared 21-root quiet-mate trial',flush=True)


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
        seconds = 1. if request['regime']=='one_second' else 3.
        cpu = time.process_time()
        result = agent._search.run(board, seconds, seconds, max_depth=64,
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
        self.process = subprocess.Popen([sys.executable, '-X', 'utf8', '-m', 'scripts.daytime_contact_allq',
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
            for regime in ('one_second', 'three_second'):
                for block, label in enumerate(('baseline', 'prototype', 'prototype', 'baseline')):
                    check_stop()
                    row = workers[label].ask(dict(root=index, regime=regime, block=block))
                    report['rows'].append(row)
                    save(OUT / 'state.json', report)
        assert len(report['rows'])==168
        report.update(status='complete',passed=True,decision='measurement_complete_needs_tactical_teacher_gate')
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
