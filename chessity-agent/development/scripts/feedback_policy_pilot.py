"""One small, predeclared playing-search check of the reward-policy checkpoint."""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/all-game-feedback-20260908/pilot'


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def worker(label):
    # No project engine imports before the selected candidate is on sys.path.
    prep = json.loads((OUT / 'preparation.json').read_text(encoding='utf-8'))
    candidate = ROOT / prep['candidates'][label]
    path = OUT / (label + '.json')
    assert not path.exists(), 'Preserve every pilot attempt'
    state = dict(status='initializing', records=[])
    save(path, state)
    try:
        sys.path.insert(0, str(candidate))
        started = time.perf_counter()
        import chess

        import agent

        state['init_seconds'] = time.perf_counter() - started
        assert state['init_seconds'] < 90
        assert Path(sys.modules['engine.compiled_core'].__file__).resolve() == candidate / 'engine/compiled_core.py'
        assert agent._search.policy is not None, 'The changed policy must be enabled'
        for row in prep['roots']:
            if any((ROOT / flag).exists() for flag in ('STOP_TRAINING', 'STOP_BENCHMARK')):
                raise InterruptedError('User stop flag')
            board = chess.Board(row['start_fen'])
            for move in row['history']:
                board.push_uci(move)
            assert board.fen() == row['fen']
            history = board.move_stack.copy()
            for key in ('ttkey', 'ttcontext', 'ttdata', 'killers', 'history'):
                getattr(agent._search, key).fill(0)
            started = time.perf_counter()
            result = agent._search.run(board, 1., 1., max_depth=64)
            seconds = time.perf_counter() - started
            legal = result.move in board.legal_moves
            restored = board.fen() == row['fen'] and board.move_stack == history
            state['records'].append(dict(id=row['id'], uci=result.move.uci(), san=board.san(result.move),
                depth=result.depth, nodes=result.nodes, seconds=seconds, legal=legal, restored=restored))
            save(path, state)
            assert legal and restored and result.depth >= 1 and seconds <= 1.25
        state['status'] = 'complete'
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        save(path, state)


def controller():
    from scripts.alien_rating_ladder import sha256
    from scripts.magnus_benchmark import manifest
    from scripts.overnight_capacity import wait_for_capacity
    from training.game_feedback import CachedTeacher, grade

    prep = json.loads((OUT / 'preparation.json').read_text(encoding='utf-8'))

    def verify():
        assert all(sha256(ROOT / p) == h for p, h in prep['source_sha256'].items())
        assert all(manifest(ROOT / path) == prep['candidate_files'][label]
                   for label, path in prep['candidates'].items())

    verify()
    for label in ('baseline', 'trained'):
        wait_for_capacity(OUT / (label + '-capacity.json'))
        with (OUT / (label + '.log')).open('w', encoding='utf-8') as log:
            process = subprocess.Popen([sys.executable, '-X', 'utf8', str(Path(__file__).resolve()),
                '--worker', label], cwd=ROOT, stdout=log, stderr=log,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            try:
                code = process.wait(timeout=130)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
                raise RuntimeError(f'{label} pilot exceeded 130s process budget') from None
        assert code == 0, f'{label} pilot failed; preserve its log'
    import chess

    probes = {label: json.loads((OUT / (label + '.json')).read_text(encoding='utf-8'))['records']
              for label in ('baseline', 'trained')}
    teacher = CachedTeacher(ROOT / 'data/postgame-feedback/cache-v1', OUT)
    report = dict(status='running', rows=[])
    try:
        for index, root in enumerate(prep['roots']):
            board = chess.Board(root['start_fen'])
            for move in root['history']:
                board.push_uci(move)
            assert board.fen() == root['fen']
            comparisons = {}
            for label in ('baseline', 'trained'):
                choice = probes[label][index]
                assert choice['id'] == root['id']
                values, regrets = [], []
                for i, budget in enumerate((80000, 320000)):
                    best = root['labels'][i]['best']
                    value = best if choice['uci'] == best['pv'][0] else teacher.analyse(
                        board, budget, chess.Move.from_uci(choice['uci']))
                    values.append(value)
                    regrets.append(max(0, best['cp'] - value['cp']) if best['cp'] is not None
                                   and value['cp'] is not None else None)
                comparisons[label] = dict(**choice, values=values, regret_cp=regrets)
            report['rows'].append(dict(id=root['id'], **comparisons))
            save(OUT / 'choice-review.json', report)
        finite = [r for r in report['rows'] if all(v is not None for label in probes
                                                   for v in r[label]['regret_cp'])]

        def major(row):
            return all(v is not None and v >= 200 for v in row['regret_cp'])

        means = {label: [sum(r[label]['regret_cp'][i] for r in finite) / len(finite)
                        for i in range(2)] for label in probes} if finite else {}
        repaired = [r['id'] for r in finite if all(
            r['baseline']['regret_cp'][i] - r['trained']['regret_cp'][i] >= 100 for i in range(2))]
        new_errors = [r['id'] for r in report['rows'] if major(r['trained']) and not major(r['baseline'])]
        new_mates = [r['id'] for r in report['rows'] if any(
            v['mate'] is not None and v['mate'] < 0 for v in r['trained']['values']) and not any(
            v['mate'] is not None and v['mate'] < 0 for v in r['baseline']['values'])]
        gate = bool(finite and repaired and not new_errors and not new_mates and all(
            a < b for a, b in zip(means['trained'], means['baseline'], strict=True)))
        report.update(status='complete', mean_regret_cp=means, repaired=repaired,
            new_major_errors=new_errors, new_mate_losses=new_mates, quality_gate_passed=gate,
            changed_moves=sum(r['baseline']['uci'] != r['trained']['uci'] for r in report['rows']),
            requested_teacher_nodes=teacher.requested_nodes,
            scope='12 exposed roots at 1s with policy enabled; diagnostic only, not Elo or a long consistency study.')
        save(OUT / 'choice-review.json', report)
        # The actual late cause of round 72 needs a deeper independent check:
        # earlier budgets agreed on the quiet defence but not the losing value.
        root = next(r for r in prep['roots'] if r['id'] == 'round-72-move-24')
        board = chess.Board(root['start_fen'])
        for move in root['history']:
            board.push_uci(move)
        best = teacher.analyse(board, 1280000)
        actual = best if best['pv'][0] == root['played'] else teacher.analyse(
            board, 1280000, chess.Move.from_uci(root['played']))
        labels = [root['labels'][-1], dict(nodes=1280000, best=best, played=actual)]
        save(OUT / 'round-72-deeper.json', dict(status='complete', root=root,
            labels=labels, **grade(labels, root['played'], board.legal_moves.count()),
            trained=False, scope='Independent refinement after the frozen fit; retain for the next training batch.'))
        verify()
    finally:
        teacher.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker', choices=('baseline', 'trained'))
    args = parser.parse_args()
    worker(args.worker) if args.worker else controller()
