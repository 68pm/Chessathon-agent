"""One bounded quiet defensive ply when the opponent has a safe legal queen check."""

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
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

from scripts import overnight_hash_scout_fixed as runner
from scripts.overnight_geometry_trial import BASE, ROOT, check_stop, digest, manifest, save

OUT = ROOT / 'runs/overnight-20260909/queen-defence-01'


THREAT_CODE = """
@njit(cache=False)
def safe_queen_check_threat(board, state):
    # Called only when side to move is not checked. This pass is a heuristic,
    # never a searched game move or a position-value label.
    side = state[0]
    king = state[4 if side == 1 else 5]
    close = False
    for dr in range(-3, 4):
        for df in range(-3, 4):
            square = king + 16 * dr + df
            if square >= 0 and not square & 0x88 and board[square] == -5 * side:
                close = True
                break
        if close:
            break
    if not close:
        return False
    probe = state.copy()
    probe[0], probe[2] = -side, -1
    tried = 0
    for move in generate(board, probe):
        source, target = move & 127, (move >> 7) & 127
        if board[source] != -5 * side:
            continue
        df = target % 16 - king % 16
        dr = target // 16 - king // 16
        if df != 0 and dr != 0 and abs(df) != abs(dr):
            continue
        if tried >= 12:
            break
        tried += 1
        old = make(board, probe, move)
        safe_check = (not attacked(board, probe[4 if side == -1 else 5], side)
            and attacked(board, king, -side) and not attacked(board, target, side))
        unmake(board, probe, move, old)
        if safe_check:
            return True
    return False
"""


def changed_source(original):
    tree = ast.parse(original)
    search = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'search')
    search.args.args.append(ast.arg(arg='queen_defences_left'))
    search.args.defaults.append(ast.Constant(1))
    calls = [n for n in ast.walk(search) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == 'search']
    assert len(calls) == 4
    for call in calls:
        call.args.append(ast.Name(id='queen_defences_left', ctx=ast.Load()))
    qindex = next(i for i, n in enumerate(search.body) if isinstance(n, ast.Assign)
                 and isinstance(n.targets[0], ast.Name) and n.targets[0].id == 'quiescence')
    search.body[qindex:qindex] = ast.parse("""
if depth <= 0 and not checked and qdepth <= 2 and queen_defences_left > 0:
    if safe_queen_check_threat(board, state):
        depth = 1
        queen_defences_left -= 1
""").body
    cindex = next(i for i, n in enumerate(search.body) if isinstance(n, ast.AugAssign)
                 and isinstance(n.target, ast.Name) and n.target.id == 'tt_context')
    search.body[cindex + 1:cindex + 1] = ast.parse(
        'tt_context ^= np.uint64(queen_defences_left) * np.uint64(0xa0761d6478bd642f)').body
    tree.body[tree.body.index(search):tree.body.index(search)] = ast.parse(THREAT_CODE).body
    ast.fix_missing_locations(tree)
    return ast.unparse(tree) + '\n'


def prepare():
    assert not OUT.exists()
    OUT.mkdir(parents=True)
    original = (BASE / 'engine/compiled_core.py').read_text(encoding='utf-8')
    changed = changed_source(original)
    prototype = OUT / 'prototype'
    shutil.copytree(BASE, prototype, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    (prototype / 'engine/compiled_core.py').write_text(changed, encoding='utf-8', newline='\n')
    experiment = ROOT / 'experiments/overnight_queen_defence_core.py'
    assert not experiment.exists()
    experiment.write_text(changed, encoding='utf-8', newline='\n')
    previous = ROOT / 'runs/overnight-20260909/bitsets-02/preparation.json'
    roots = json.loads(previous.read_text(encoding='utf-8'))['roots']
    assert len(roots) == len({r['id'] for r in roots}) == 22
    save(OUT / 'preparation.json', dict(candidates={
        'baseline': str(BASE.relative_to(ROOT)), 'prototype': str(prototype.relative_to(ROOT))},
        candidate_files={'baseline': manifest(BASE), 'prototype': manifest(prototype)}, roots=roots,
        source_sha256={str(p.relative_to(ROOT)): digest(p) for p in (
            ROOT / 'scripts/overnight_queen_defence.py', ROOT / 'tests/test_overnight_queen_defence.py',
            ROOT / 'scripts/overnight_hash_scout_fixed.py', ROOT / 'scripts/overnight_geometry_trial.py',
            ROOT / 'docs/OVERNIGHT_QUEEN_DEFENCE_PLAN_20260909.md', previous, experiment)},
        scope='One defensive ply from a safe legal queen-check opportunity;22 exposed roots, no Elo.'))


class ThreatWorker(runner.WarmWorker):
    def __init__(self, label):
        self.label = label
        self.log = (OUT / f'{label}.log').open('w', encoding='utf-8')
        self.answers = queue.Queue()
        self.process = subprocess.Popen([sys.executable, '-X', 'utf8', '-m',
            'scripts.overnight_queen_defence', '--worker', label], cwd=ROOT,
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
        runner.OUT = OUT
        runner.worker(args.worker)
    else:
        controller()
