"""One bounded quiet-check continuation pilot, with proof and regression gates."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import manifest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/improvement-loop-20260907/cycle-35'


def stop_check():
    if any((ROOT / name).exists() for name in ['STOP_TRAINING', 'STOP_BENCHMARK']):
        raise InterruptedError('User stop flag')


def verify(prep):
    for label in ['baseline', 'prototype']:
        assert manifest(ROOT / prep[label]) == prep[label + '_files']
    for name, digest in prep['source_files'].items():
        assert sha256(ROOT / name) == digest, name
    for name, digest in prep['inputs'].items():
        assert sha256(OUT / name) == digest, name


def worker(label):
    path = OUT / (label + '.json')
    assert not path.exists(), 'Preserve every attempt'
    prep = json.loads((OUT / 'preparation.json').read_text())
    verify(prep)
    candidate = ROOT / prep[label]
    report = dict(status='initializing', pid=os.getpid(), label=label,
        preparation_sha256=sha256(OUT / 'preparation.json'), proof={}, clock=[])
    save_json(path, report)
    try:
        stop_check()
        sys.path.insert(0, str(candidate.resolve()))
        tick = time.perf_counter()
        import chess
        import numpy as np

        import agent

        driver = sys.modules['engine.compiled_driver']
        core, arrays = driver.core, driver.arrays
        assert Path(core.__file__).resolve() == (candidate / 'engine/compiled_core.py').resolve()
        report['init_seconds'] = time.perf_counter() - tick
        assert report['init_seconds'] <= 90
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

        def analyze(row, depth, ply, extensions, quiet_credits, nodes=500000, seconds=8):
            stop_check()
            clear()
            board = restore(row)
            pieces, state = arrays(board)
            saved_pieces, saved_state = pieces.copy(), state.copy()
            accumulator = core.build_accumulator(pieces, search.weights, search.bias)
            saved_accumulator = accumulator.copy()
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
            context = np.uint64(sum(map(int, past)) & ((1 << 64) - 1))
            control = np.array([0, 0, nodes], dtype=np.int64)
            tick = time.perf_counter()
            score = core.search(pieces, state, depth, -31000, 31000, ply, 0,
                hashes, len(past), context, search.ttkey, search.ttcontext, search.ttdata,
                search.killers, search.history, control, tick + seconds, search.weights,
                search.bias, search.output, search.blend, search.conversion, search.reductions,
                accumulator, extensions, quiet_credits, 0)
            elapsed = time.perf_counter() - tick
            assert np.array_equal(pieces, saved_pieces) and np.array_equal(state, saved_state)
            assert np.array_equal(accumulator, saved_accumulator) and list(hashes[:len(past)]) == past
            assert int(control[0]) <= nodes and elapsed <= seconds + .25
            return dict(id=row['id'], depth=depth, quiet_credits=quiet_credits,
                complete=not bool(control[1]), score_root=int(score) * (1 if board.turn == row['root_white'] else -1)
                if not control[1] else None, nodes=int(control[0]), seconds=elapsed)

        if label == 'prototype':
            report['status'] = 'correctness'
            spec = json.loads((OUT / 'proof.json').read_text())
            rng = np.random.default_rng(2026090835)
            board = chess.Board()
            for index in range(240):
                stop_check()
                if board.is_game_over() or index % 80 == 0:
                    board = chess.Board()
                pieces, state = arrays(board)
                saved = pieces.copy(), state.copy()
                for side in [chess.WHITE, chess.BLACK]:
                    expected = any(chess.square_distance(q, board.king(not side)) <= 2 for q in board.pieces(chess.QUEEN, side))
                    assert bool(core.queen_near_king(pieces, state, 1 if side else -1)) == expected
                assert np.array_equal(pieces, saved[0]) and np.array_equal(state, saved[1])
                legal = list(board.legal_moves)
                board.push(legal[int(rng.integers(len(legal)))])
            report['proof']['geometry'] = dict(positions=240, colors=2, passed=True)
            report['proof']['disabled'] = []
            for row in spec['disabled']:
                result = analyze(row, 5, 1, 2, 0)
                report['proof']['disabled'].append(result)
                save_json(path, report)
                assert result['complete'] and result['score_root'] == row['expected'], 'Disabled quiet-check score parity failed'
            report['proof']['mates'] = []
            for row in spec['mates']:
                for credits in [0, 4]:
                    result = analyze(row, 0, 0, 0, credits)
                    report['proof']['mates'].append(result)
                    save_json(path, report)
                    assert result['complete'], 'Mating-sequence proof exhausted its resource bound'
                    assert result['score_root'] > 29900 if credits == 4 else abs(result['score_root']) < 29000
            report['proof']['terminal'] = []
            for row in spec['terminal']:
                result = analyze(row, 0, 0, 2, 4)
                report['proof']['terminal'].append(result)
                save_json(path, report)
                assert result['complete'] and result['score_root'] == row['expected']
            interrupted = analyze(spec['interrupt'], 12, 0, 2, 4, nodes=512)
            report['proof']['interrupted'] = interrupted
            save_json(path, report)
            assert not interrupted['complete'] and interrupted['nodes'] == 512
            report['proof']['passed'] = True
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


def main():
    from scripts.improvement_king_coordination_gate import child
    from scripts.overnight_capacity import wait_for_capacity

    assert not (OUT / 'context.json').exists(), 'No unchanged pilot retries'
    prep = json.loads((OUT / 'preparation.json').read_text())
    verify(prep)
    assert sha256(OUT / 'choice-cache.jsonl') == prep['inputs']['choice-cache.seed.jsonl']
    state = dict(status='running', stage='prototype-correctness-and-clock',
        preparation_sha256=sha256(OUT / 'preparation.json'))
    save_json(OUT / 'context.json', state)
    try:
        reports = {}
        for label in ['prototype', 'baseline']:
            state['stage'] = label + '-worker'
            save_json(OUT / 'context.json', state)
            wait_for_capacity(OUT / (label + '-capacity.json'))
            child(['-m', 'scripts.near_queen_checks_pilot', '--worker', label], OUT / (label + '.log'), timeout=360)
            reports[label] = json.loads((OUT / (label + '.json')).read_text())
            assert reports[label]['status'] == 'complete'
        assert reports['prototype']['proof']['passed']
        repeats = {label: sum(r['repeats_played'] for r in report['clock']) for label, report in reports.items()}
        target = 'rated52:game-002-ply-042'
        changed = next(r['uci'] for r in reports['prototype']['clock'] if r['id'] == target) != 'h4f2'
        cheap = repeats['prototype'] < repeats['baseline'] and changed
        passed, teacher = False, None
        if cheap:
            from training.mistake_replay import review_choices

            state['stage'] = 'bounded-teacher-review'
            save_json(OUT / 'context.json', state)
            roots = [json.loads(line) for line in (OUT / 'roots.jsonl').read_text().splitlines()]
            reviews = {}
            for label in ['baseline', 'prototype']:
                wait_for_capacity(OUT / (label + '-teacher-capacity.json'))
                reviews[label] = review_choices([dict(root=r) for r in roots], reports[label]['clock'], OUT / 'choice-cache.jsonl')
                save_json(OUT / (label + '-review.json'), reviews[label])
            errors, mates = [], []
            for a, b in zip(reviews['baseline']['records'], reviews['prototype']['records'], strict=True):
                assert a['id'] == b['id']
                if max(a['regret']) < 200 and min(b['regret']) >= 200:
                    errors.append(a['id'])
                if b['mate_loss'] and not a['mate_loss']:
                    mates.append(a['id'])
            repaired = next(max(r['regret']) <= 50 for r in reviews['prototype']['records'] if r['id'] == target)
            means = {label: review['mean_regret'] for label, review in reviews.items()}
            teacher = dict(mean_regret=means, new_errors=errors, new_mates=mates, repaired_target=repaired,
                new_teacher_nodes=sum(r['new_teacher_nodes'] for r in reviews.values()))
            assert teacher['new_teacher_nodes'] <= 16800000
            passed = bool(not errors and not mates and repaired
                and all(b < a for a, b in zip(means['baseline'], means['prototype'], strict=True)))
        verify(prep)
        gate = dict(status='complete', passed=passed, cheap_pass=cheap, clock_repeats=repeats,
            target_changed=changed, teacher_review=teacher, automatic_promotion=False, games=0, fitting_updates=0)
        save_json(OUT / 'gate.json', gate)
        state.update(status='complete', stage='awaiting_critique', passed=passed)
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
