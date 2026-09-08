"""Canonical incremental EP hashes plus root scouts, with alternating warm workers."""

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

from scripts.overnight_geometry_trial import BASE, ROOT, check_stop, digest, manifest, save

OUT = ROOT / 'runs/overnight-20260909/hash-scout-01'

HASH_CODE = '''
@njit(cache=False)
def ep_hash(board, state):
    """Only a legal en-passant capture contributes to the repetition key."""
    ep, side = state[2], state[0]
    if ep >= 0:
        for delta in (-1, 1):
            source, victim = ep - 16 * side + delta, ep - 16 * side
            if source >= 0 and not source & 0x88 and board[source] == side and board[victim] == -side:
                board[source], board[victim], board[ep] = 0, 0, side
                valid = not attacked(board, state[4 if side == 1 else 5], -side)
                board[source], board[victim], board[ep] = side, -side, 0
                if valid:
                    return ZEP[ep]
    return np.uint64(0)


@njit(cache=False)
def hash_after_move(parent_key, parent_ep, board, state, move, old):
    """Exact legal child key, including EP without falling back to a board scan."""
    source, target, flags = move & 127, (move >> 7) & 127, move >> 17
    piece, captured = old[0], old[1]
    key = parent_key ^ parent_ep ^ ZSIDE ^ ZCASTLE[old[2]] ^ ZCASTLE[state[1]]
    key ^= ZPIECE[piece + 6, source] ^ ZPIECE[board[target] + 6, target]
    if captured:
        key ^= ZPIECE[captured + 6, target]
    if flags & 1:
        key ^= ZPIECE[state[0] + 6, target + 16 * state[0]]
    if flags & 2:
        rook = -4 * state[0]
        rfrom = (source // 16) * 16 + (7 if target > source else 0)
        rto = source + (1 if target > source else -1)
        key ^= ZPIECE[rook + 6, rfrom] ^ ZPIECE[rook + 6, rto]
    return key ^ ep_hash(board, state)


'''


def prepare():
    assert not OUT.exists(), 'Single-use preparation; preserve failed trials'
    OUT.mkdir(parents=True)
    original = (BASE / 'engine/compiled_core.py').read_text(encoding='utf-8')
    scout_path = ROOT / 'experiments/competition_root_pvs_core.py'
    scout_source = scout_path.read_text(encoding='utf-8')
    marker = '@njit(cache=False)\ndef root_iteration('
    source = original[:original.index(marker)] + scout_source[scout_source.index(marker):]
    marker_hash = '@njit(cache=False)\ndef insufficient('
    source = source.replace(marker_hash, HASH_CODE + marker_hash, 1)
    source = source.replace('    best, bestmove, legal_count = stand, 0, 0\n',
        '    parent_ep = ep_hash(board, state)\n    best, bestmove, legal_count = stand, 0, 0\n', 1)
    source = source.replace('        childkey = position_hash(board, state)\n',
        '        childkey = hash_after_move(key, parent_ep, board, state, move, old)\n', 1)
    root_start = source.index(marker)
    source = source[:root_start] + source[root_start:].replace(
        '    best, bestmove = -31000, previous\n',
        '    parent_ep = ep_hash(board, state)\n    parent_key = hashes[hlen - 1]\n'
        '    best, bestmove = -31000, previous\n', 1).replace(
        '        key = position_hash(board, state)\n',
        '        key = hash_after_move(parent_key, parent_ep, board, state, move, old)\n', 1)
    before_ast, after_ast = ast.parse(original), ast.parse(source)
    allowed = {'search', 'root_iteration', 'hash_after_move', 'ep_hash'}
    def unchanged(tree):
        return [ast.dump(n) for n in tree.body if not (isinstance(n, ast.FunctionDef) and n.name in allowed)]
    assert unchanged(before_ast) == unchanged(after_ast)
    prototype = OUT / 'prototype'
    shutil.copytree(BASE, prototype, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    (prototype / 'engine/compiled_core.py').write_text(source, encoding='utf-8', newline='\n')
    experimental = ROOT / 'experiments/overnight_hash_scout_core.py'
    assert not experimental.exists()
    experimental.write_text(source, encoding='utf-8', newline='\n')
    prior = ROOT / 'runs/all-game-feedback-20260908/pilot/preparation.json'
    roots = json.loads(prior.read_text(encoding='utf-8'))['roots']
    assert len(roots) == 12
    save(OUT / 'preparation.json', dict(created_utc=datetime.now(timezone.utc).isoformat(),
        candidates={'baseline': str(BASE.relative_to(ROOT)), 'prototype': str(prototype.relative_to(ROOT))},
        candidate_files={'baseline': manifest(BASE), 'prototype': manifest(prototype)}, roots=roots,
        source_sha256={str(p.relative_to(ROOT)): digest(p) for p in
            (Path(__file__), ROOT / 'scripts/overnight_geometry_trial.py', scout_path, prior, experimental)},
        scope='New EP-complete hashing and root scout integration on53; exposed development, not Elo.'))
    print('Prepared ' + str(OUT), flush=True)


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
        result = agent._search.run(board, seconds, seconds, max_depth=4 if fixed else 64,
                                   max_nodes=2000000 if fixed else 2**60)
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
        self.process = subprocess.Popen([sys.executable, '-X', 'utf8', '-m', 'scripts.overnight_hash_scout',
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
        completed = all(r['depth'] == 4 or abs(r['score']) > 29900 for r in fixed)
        parity, ratios, node_ratios = True, [], []
        for index in range(len(prep['roots'])):
            rows = [r for r in fixed if r['root'] == index]
            parity &= len({(r['score'], r['depth']) for r in rows}) == 1
            a = [r for r in rows if r['label'] == 'baseline']
            b = [r for r in rows if r['label'] == 'prototype']
            ratios.append(statistics.mean(r['cpu_seconds'] for r in a) /
                          max(1e-9, statistics.mean(r['cpu_seconds'] for r in b)))
            node_ratios.append(statistics.mean(r['nodes'] for r in b) / statistics.mean(r['nodes'] for r in a))
        depths = {label: statistics.mean(r['depth'] for r in report['rows']
                  if r['regime'] == 'clock' and r['label'] == label) for label in workers}
        report.update(fixed_completed=completed, fixed_score_parity=parity,
            median_cpu_speedup=statistics.median(ratios), cpu_ratios=ratios,
            median_node_ratio=statistics.median(node_ratios), clock_mean_depth=depths)
        report['passed'] = bool(completed and parity and statistics.median(ratios) >= 1.10
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
