"""One fixed legal-check evaluation pilot; preserve every attempt and failure."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import manifest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/improvement-loop-20260907/cycle-38'


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
        preparation_sha256=sha256(OUT / 'preparation.json'), proof={}, attempts=[], leaves=[], clock=[])
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
        save_json(path, report)
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

        def analyze(row, depth=0, extensions=0, nodes=100000, seconds=2):
            stop_check()
            board = restore(row)
            clear()
            pieces, state = arrays(board)
            saved_pieces, saved_state = pieces.copy(), state.copy()
            accumulator = core.build_accumulator(pieces, search.weights, search.bias)
            saved_accumulator = accumulator.copy()
            past, replay = [], board.copy(stack=True)
            for _ in range(min(board.halfmove_clock, len(board.move_stack)) + 1):
                p, s = arrays(replay)
                past.append(core.position_hash(p, s))
                if not replay.move_stack:
                    break
                replay.pop()
            past.reverse()
            hashes = np.zeros(800, dtype=np.uint64)
            hashes[:len(past)] = past
            context = np.uint64(sum(map(int, past)) & ((1 << 64) - 1))
            control = np.array([0, 0, nodes], dtype=np.int64)
            signatures = tuple(map(str, core.search.signatures))
            tick = time.perf_counter()
            score = core.search(pieces, state, depth, -31000, 31000, 0, 0,
                hashes, len(past), context, search.ttkey, search.ttcontext, search.ttdata,
                search.killers, search.history, control, tick + seconds, search.weights,
                search.bias, search.output, search.blend, search.conversion, search.reductions,
                accumulator, extensions, 4, 0)
            elapsed = time.perf_counter() - tick
            restored = (np.array_equal(pieces, saved_pieces) and np.array_equal(state, saved_state)
                and np.array_equal(accumulator, saved_accumulator) and list(hashes[:len(past)]) == past)
            added = [s for s in map(str, core.search.signatures) if s not in signatures]
            within_bounds = int(control[0]) <= nodes and elapsed <= seconds + .25
            valid = restored and within_bounds and not added
            complete = bool(valid and not control[1])
            measured = dict(id=row['id'], complete=complete,
                score_root=int(score) * (1 if board.turn == row['root_white'] else -1) if complete else None,
                nodes=int(control[0]), seconds=elapsed, depth=depth, limits=dict(nodes=nodes, seconds=seconds),
                restored=bool(restored), within_bounds=within_bounds, added_signatures=added)
            report['attempts'].append(measured)
            save_json(path, report)
            assert valid, 'Measured call failed; raw attempt preserved'
            return measured

        leaves = json.loads((OUT / 'leaves.json').read_text())
        assert len(leaves) == 23
        if label == 'prototype':
            report['status'] = 'correctness'

            def oracle(board, side):
                if not board.pieces(chess.QUEEN, side):
                    return 0
                replay = board.copy(stack=False)
                replay.turn = side
                replay.ep_square = None
                found = {}
                for move in list(replay.legal_moves):
                    piece = replay.piece_type_at(move.from_square)
                    if piece not in [2, 3, 4, 5] or replay.piece_at(move.to_square) or replay.is_castling(move):
                        continue
                    replay.push(move)
                    direct = move.to_square in replay.attackers(side, replay.king(not side))
                    if direct and not replay.is_attacked_by(not side, move.to_square):
                        found[move.from_square] = {2: 40, 3: 40, 4: 60, 5: 80}[piece]
                    replay.pop()
                return min(240, sum(found.values()))

            rng = np.random.default_rng(2026090838)
            board = chess.Board()
            positions = []
            for index in range(120):
                stop_check()
                if board.is_game_over() or index % 40 == 0:
                    board = chess.Board()
                positions.append(board.copy(stack=False))
                legal = list(board.legal_moves)
                board.push(legal[int(rng.integers(len(legal)))])
            positions += [restore(row) for row in leaves]
            report['proof']['oracle'] = dict(positions=len(positions), colors=2, mirrors=True, checked=0)
            for board in positions:
                stop_check()
                pieces, state = arrays(board)
                mirrored = board.mirror()
                mp, ms = arrays(mirrored)
                saved = pieces.copy(), state.copy(), mp.copy(), ms.copy()
                for side in [chess.WHITE, chess.BLACK]:
                    score = int(core.safe_check_opportunities(pieces, state, 1 if side else -1))
                    reflection = int(core.safe_check_opportunities(mp, ms, -1 if side else 1))
                    assert score == oracle(board, side) == reflection
                assert all(np.array_equal(a, b) for a, b in zip([pieces, state, mp, ms], saved, strict=True))
                assert core.classical(pieces, state, False) == core.classical(mp, ms, False)
                report['proof']['oracle']['checked'] += 1
            spec = json.loads((OUT / 'proof.json').read_text())
            report['proof']['mates'] = []
            for row in spec['mates']:
                result = analyze(row, nodes=500000, seconds=8)
                report['proof']['mates'].append(result)
                save_json(path, report)
                assert result['complete'] and result['score_root'] > 29900
            report['proof']['terminal'] = []
            for row in spec['terminal']:
                result = analyze(row, extensions=2)
                report['proof']['terminal'].append(result)
                save_json(path, report)
                assert result['complete'] and result['score_root'] == row['expected']
            result = analyze(spec['interrupt'], depth=12, extensions=2, nodes=512)
            report['proof']['interrupted'] = result
            save_json(path, report)
            assert not result['complete'] and result['nodes'] == 512
            report['proof']['passed'] = True

        report['status'] = 'endpoint-probes'
        for row in leaves:
            measured = analyze(row)
            board = restore(row)
            pieces, state = arrays(board)
            factor = 1 if board.turn == row['root_white'] else -1
            measured = dict(measured, static_root=int(core.classical(pieces, state, False)) * factor)
            if label == 'prototype':
                measured['safe_checks_white'] = int(core.safe_check_opportunities(pieces, state, 1))
                measured['safe_checks_black'] = int(core.safe_check_opportunities(pieces, state, -1))
            report['leaves'].append(measured)
            save_json(path, report)

        report['status'] = 'clock-probes'
        roots = [json.loads(line) for line in (OUT / 'roots.jsonl').read_text().splitlines()]
        assert len(roots) == len({r['id'] for r in roots}) == 24
        for row in roots:
            stop_check()
            board = restore(row)
            stack = list(board.move_stack)
            clear()
            signatures = tuple(map(str, core.search.signatures))
            tick = time.perf_counter()
            result = search.run(board, seconds=1., soft=1., max_depth=64)
            elapsed = time.perf_counter() - tick
            restored = board.fen() == row['fen'] and board.move_stack == stack
            added = [s for s in map(str, core.search.signatures) if s not in signatures]
            report['clock'].append(dict(id=row['id'], uci=result.move.uci(), depth=result.depth,
                score=result.score, nodes=result.nodes, seconds=result.elapsed, wall_seconds=elapsed,
                repeats_played=result.move.uci() == row['played'], restored=restored, added_signatures=added))
            save_json(path, report)
            assert result.move in board.legal_moves and restored and not added
            assert result.depth >= 1 and elapsed <= 1.25
        verify(prep)
        report['status'] = 'complete'
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(path, report)


def main():
    import statistics

    from scripts.improvement_king_coordination_gate import child
    from scripts.overnight_capacity import wait_for_capacity

    assert not (OUT / 'context.json').exists(), 'No unchanged pilot retries'
    prep = json.loads((OUT / 'preparation.json').read_text())
    verify(prep)
    assert sha256(OUT / 'choice-cache.jsonl') == prep['inputs']['choice-cache.seed.jsonl']
    state = dict(status='running', stage='prototype-correctness', preparation_sha256=sha256(OUT / 'preparation.json'))
    save_json(OUT / 'context.json', state)
    try:
        reports = {}
        for label in ['prototype', 'baseline']:
            state['stage'] = label + '-worker'
            save_json(OUT / 'context.json', state)
            wait_for_capacity(OUT / (label + '-capacity.json'))
            child(['-m', 'scripts.safe_check_opportunities_pilot', '--worker', label], OUT / (label + '.log'), timeout=360)
            reports[label] = json.loads((OUT / (label + '.json')).read_text())
            assert reports[label]['status'] == 'complete'
        assert reports['prototype']['proof']['passed']
        leaves = json.loads((OUT / 'leaves.json').read_text())
        all_complete = all(row['complete'] for report in reports.values() for row in report['leaves'])
        leaf_gate, leaf_detail = False, None
        if all_complete:
            errors = {label: [[abs(value['score_root'] - target['teacher'][i]['cp_root']) for i in [0, 1]]
                for value, target in zip(report['leaves'], leaves, strict=True)] for label, report in reports.items()}
            means = {label: [statistics.mean(r[i] for r in values) for i in [0, 1]] for label, values in errors.items()}
            new_errors = [row['id'] for row, a, b in zip(leaves, errors['baseline'], errors['prototype'], strict=True)
                if max(a) < 200 and min(b) >= 200]
            leaf_gate = all(b < a for a, b in zip(means['baseline'], means['prototype'], strict=True)) and not new_errors
            leaf_detail = dict(mean_absolute_error=means, new_errors=new_errors, passed=leaf_gate)
        repeats = {label: sum(r['repeats_played'] for r in report['clock']) for label, report in reports.items()}
        recent_changed = any(r['id'].startswith('v53-rated-loss-') and not r['repeats_played'] for r in reports['prototype']['clock'])
        cheap = leaf_gate and repeats['prototype'] < repeats['baseline'] and recent_changed
        teacher, passed = None, False
        if cheap:
            from training.mistake_replay import review_choices

            roots = [json.loads(line) for line in (OUT / 'roots.jsonl').read_text().splitlines()]
            reviews = {}
            state['stage'] = 'bounded-teacher-review'
            save_json(OUT / 'context.json', state)
            for label in ['baseline', 'prototype']:
                wait_for_capacity(OUT / (label + '-teacher-capacity.json'))
                reviews[label] = review_choices([dict(root=r) for r in roots], reports[label]['clock'], OUT / 'choice-cache.jsonl')
                save_json(OUT / (label + '-review.json'), reviews[label])
            errors, mates, repaired = [], [], []
            for a, b in zip(reviews['baseline']['records'], reviews['prototype']['records'], strict=True):
                assert a['id'] == b['id']
                if max(a['regret']) < 200 and min(b['regret']) >= 200:
                    errors.append(a['id'])
                if b['mate_loss'] and not a['mate_loss']:
                    mates.append(a['id'])
                if a['id'].startswith('v53-rated-loss-') and all(x - y >= 100 for x, y in zip(a['regret'], b['regret'], strict=True)):
                    repaired.append(a['id'])
            old_repair = next(max(r['regret']) <= 50 for r in reviews['prototype']['records'] if r['id'] == 'rated52:game-002-ply-042')
            means = {label: review['mean_regret'] for label, review in reviews.items()}
            teacher = dict(mean_regret=means, new_errors=errors, new_mates=mates, repaired_recent=repaired,
                old_repair_preserved=old_repair, new_teacher_nodes=sum(r['new_teacher_nodes'] for r in reviews.values()))
            assert teacher['new_teacher_nodes'] <= 19200000
            passed = bool(not errors and not mates and repaired and old_repair
                and all(b < a for a, b in zip(means['baseline'], means['prototype'], strict=True)))
        verify(prep)
        gate = dict(status='complete', passed=passed, cheap_pass=cheap, endpoint_probes_complete=all_complete,
            endpoint_gate=leaf_detail, clock_repeats=repeats, recent_changed=recent_changed,
            teacher_review=teacher, automatic_promotion=False, games=0, fitting_updates=0)
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
