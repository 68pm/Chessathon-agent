"""One bounded quiet defensive ply when the opponent has a safe legal queen check."""

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

from scripts import overnight_hash_scout_fixed as runner
from scripts.overnight_geometry_trial import ROOT, check_stop, digest, manifest, save

OUT = ROOT / 'runs/overnight-20260909/guarded-leaf-01'
BASE = ROOT / 'runs/overnight-20260909/coalesced-search-01/prototype'


def prepare():
    from scripts.guarded_leaf_transform import changed_source, driver_source
    from scripts.feedback_matches_windows import feedback_path
    assert not OUT.exists(), 'Preserve partial or completed trials.'
    parent = ROOT / 'runs/overnight-20260909/pawn-masks-01'
    parent_prep = json.loads((parent / 'preparation.json').read_text(encoding='utf-8'))
    assert manifest(parent / 'prototype') == parent_prep['candidate_files']['prototype']
    model = ROOT / 'runs/overnight-20260909/rule-value-01/value.npz'
    assert digest(model) == '90bf01a13aa71751727f970f754410b1e40a68b021665ba49949a8cdd2683b9a'
    OUT.mkdir()
    prototype = OUT / 'prototype'
    shutil.copytree(parent / 'prototype', prototype, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    core = prototype / 'engine/compiled_core.py'
    text = changed_source(core.read_text(encoding='utf-8'))
    core.write_text(text, encoding='utf-8', newline='\n')
    experiment = ROOT / 'experiments/overnight_guarded_leaf_core.py'
    assert not experiment.exists()
    experiment.write_text(text, encoding='utf-8', newline='\n')
    driver = prototype / 'engine/compiled_driver.py'
    driver.write_text(driver_source(driver.read_text(encoding='utf-8')), encoding='utf-8', newline='\n')
    shutil.copy2(model, prototype / 'models/value.npz')
    runtime = prototype / 'runtime.json'
    config = json.loads(runtime.read_text(encoding='utf-8'))
    config.update(residual_value=True, value_blend=.5)
    save(runtime, config)
    roots = parent_prep['roots'].copy()
    directory = ROOT / 'runs/improvement-loop-20260907/n9-dev-2400/rated-prototype/postgame-feedback/reviews/games'
    reviews = sorted(feedback_path(directory).glob('*/review.json'))
    for path in reviews:
        doc = json.loads(path.read_text(encoding='utf-8'))
        assert doc['status'] == 'complete'
        game = doc['identity']['game']
        wanted = [23] if game['source_game_id'] == '1' else [25, 26, 35]
        for number in wanted:
            row = next(r for r in doc['rows'] if r['fullmove'] == number)
            roots.append(dict(id=f'd65-game-{game["source_game_id"]}-move-{number}',
                start_fen=row['start_fen'], history=row['history'], fen=row['fen'],
                actual_played=row['played'], source_game_id=game['game_key']))
    assert len(roots) == 26 and len({r['id'] for r in roots}) == 26
    sources = {str(p.relative_to(feedback_path(ROOT))): digest(p) for p in reviews}
    sources.update({str(p.relative_to(ROOT)): digest(p) for p in (
        Path(__file__), ROOT / 'scripts/guarded_leaf_transform.py',
        ROOT / 'scripts/overnight_check_prefilter.py', ROOT / 'scripts/overnight_hash_scout_fixed.py',
        ROOT / 'scripts/overnight_geometry_trial.py', parent / 'preparation.json', model,
        BASE / 'engine/compiled_core.py', ROOT / 'training/rule_value.py',
        ROOT / 'tests/test_overnight_guarded_leaf.py',
        ROOT / 'docs/OVERNIGHT_GUARDED_LEAF_PLAN_20260909.md', experiment)})
    save(OUT / 'preparation.json', dict(candidates={
        'baseline': str(BASE.relative_to(ROOT)), 'prototype': str(prototype.relative_to(ROOT))},
        candidate_files={'baseline': manifest(BASE), 'prototype': manifest(prototype)}, roots=roots,
        source_sha256=sources, model_sha256=digest(model), blend=.5, per_root_order='ABBA',
        scope='New guarded leaf architecture using frozen existing parameters; no new fit. Classical through move12 and phase<=8. All roots exposed development data; no strength or Elo claim.'))


def worker(label):
    prep = json.loads((OUT / 'preparation.json').read_text(encoding='utf-8'))
    candidate = ROOT / prep['candidates'][label]
    sys.path.insert(0, str(candidate))
    tick = time.perf_counter()
    import chess

    import agent

    init = time.perf_counter() - tick
    assert Path(sys.modules['engine.compiled_core'].__file__).resolve() == candidate / 'engine/compiled_core.py'
    compiled = sys.modules['engine.compiled_core'].search
    print(json.dumps(dict(status='ready', init_seconds=init, compiled_search_variants=len(compiled.signatures),
        search_signatures=[str(s) for s in compiled.signatures])), flush=True)
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
        result = agent._search.run(board, seconds, seconds, max_depth=64,
                                   max_nodes=250000 if fixed else 2**60)
        cpu = time.process_time() - tick
        assert result.move in board.legal_moves
        assert board.fen() == root['fen'] and board.move_stack == history
        assert result.elapsed <= seconds + .3
        print(json.dumps(dict(**request, id=root['id'], label=label, uci=result.move.uci(),
            score=result.score, depth=result.depth, nodes=result.nodes,
            seconds=result.elapsed, cpu_seconds=cpu)), flush=True)

class ThreatWorker(runner.WarmWorker):
    def __init__(self, label):
        self.label = label
        self.log = (OUT / f'{label}.log').open('w', encoding='utf-8')
        self.answers = queue.Queue()
        self.process = subprocess.Popen([sys.executable, '-X', 'utf8', '-m',
            'scripts.overnight_guarded_leaf', '--worker', label], cwd=ROOT,
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
    report = dict(status='running', passed=False, workers={}, rows=[])
    workers = {}
    save(OUT / 'state.json', report)
    try:
        for path, expected in prep['source_sha256'].items():
            assert digest(ROOT / path) == expected
        for label in ('prototype', 'baseline'):
            check_stop()
            wait_for_capacity(OUT / f'{label}-capacity.json', minimum_memory_mb=1400, wait_seconds=120)
            workers[label] = ThreatWorker(label)
            report['workers'][label] = dict(pid=workers[label].process.pid, status='initializing')
            save(OUT / 'state.json', report)
            ready = workers[label].receive(90)
            report['workers'][label].update(ready)
            save(OUT / 'state.json', report)
            assert ready['init_seconds'] < 90
        for index in range(len(prep['roots'])):
            for block, label in enumerate(('baseline', 'prototype', 'prototype', 'baseline')):
                check_stop()
                row = workers[label].ask(dict(root=index, regime='clock', block=block))
                report['rows'].append(row)
                save(OUT / 'state.json', report)
        report['status'] = 'search_complete'
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        for worker_process in workers.values():
            worker_process.close()
        save(OUT / 'state.json', report)
    # Teacher runs only after both competing search workers have exited.
    import chess

    from training.game_feedback import CachedTeacher

    check_stop()
    wait_for_capacity(OUT / 'teacher-capacity.json', minimum_memory_mb=1400, wait_seconds=120)
    teacher = CachedTeacher(ROOT / 'data/postgame-feedback/cache-v1', OUT)
    report['review'] = []
    try:
        for index, root in enumerate(prep['roots']):
            check_stop()
            board = chess.Board(root['start_fen'])
            for uci in root['history']:
                board.push_uci(uci)
            assert board.fen() == root['fen']
            choices = [r for r in report['rows'] if r['root'] == index]
            bests = [teacher.analyse(board, budget) for budget in (80000, 320000)]
            values = {}
            for uci in sorted({r['uci'] for r in choices}):
                values[uci] = [best if best['pv'][0] == uci else teacher.analyse(
                    board, budget, chess.Move.from_uci(uci))
                    for budget, best in zip((80000, 320000), bests, strict=True)]
            reviewed = []
            for choice in choices:
                selected = values[choice['uci']]
                regret = [max(0, best['cp'] - value['cp'])
                          if best['cp'] is not None and value['cp'] is not None else None
                          for best, value in zip(bests, selected, strict=True)]
                reviewed.append(dict(**choice, values=selected, regret_cp=regret,
                    major=all(v is not None and v >= 200 for v in regret),
                    mate_loss=any(v['mate'] is not None and v['mate'] < 0 for v in selected)))
            report['review'].append(dict(id=root['id'], best=bests, choices=reviewed))
            save(OUT / 'state.json', report)
        finite = [r for r in report['review'] if all(v is not None for c in r['choices'] for v in c['regret_cp'])]
        means = {label: [statistics.mean(c['regret_cp'][i] for r in finite for c in r['choices']
                         if c['label'] == label) for i in range(2)] for label in workers}
        new_major, new_mate, repairs = [], [], []
        for row in report['review']:
            a = [c for c in row['choices'] if c['label'] == 'baseline']
            b = [c for c in row['choices'] if c['label'] == 'prototype']
            if sum(c['major'] for c in b) > sum(c['major'] for c in a):
                new_major.append(row['id'])
            if sum(c['mate_loss'] for c in b) > sum(c['mate_loss'] for c in a):
                new_mate.append(row['id'])
            if row in finite and all(statistics.mean(c['regret_cp'][i] for c in a) -
                statistics.mean(c['regret_cp'][i] for c in b) >= 100 for i in range(2)):
                repairs.append(row['id'])
        target = [r for r in report['rows'] if r['id'] == 'round-72-move-24']
        depths = {label: statistics.mean(r['depth'] for r in target if r['label'] == label) for label in workers}
        gate = bool(repairs and not new_major and not new_mate and
                    all(a <= b for a, b in zip(means['prototype'], means['baseline'], strict=True)))
        report.update(status='complete', passed=gate, mean_regret_cp=means,
            new_major=new_major, new_mate=new_mate, repaired=repairs, target_depths=depths,
            requested_teacher_nodes=teacher.requested_nodes,
            decision='needs_read_only_validation_and_short_matches' if gate else 'reject_quality_gate')
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        teacher.close()
        report['completed_utc'] = datetime.now(timezone.utc).isoformat()
        report['frozen_candidates'] = all(manifest(ROOT / p) == prep['candidate_files'][label]
                                          for label, p in prep['candidates'].items())
        if not report['frozen_candidates']:
            report.update(status='failed', passed=False, error='Frozen candidate changed')
        save(OUT / 'state.json', report)
        print(json.dumps({k: v for k, v in report.items() if k not in ('rows', 'review')}), flush=True)


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
