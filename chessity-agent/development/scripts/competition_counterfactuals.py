"""Capture exact-table student continuations and independently review descendants."""
import argparse
import json
import os
import sys
import time
from pathlib import Path

from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import manifest

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/competition-counterfactuals-20260908'


def stop_check():
    if any((ROOT / flag).exists() for flag in ['STOP_TRAINING', 'STOP_BENCHMARK']):
        raise InterruptedError('User stop flag')


def verify(prep):
    assert manifest(ROOT / prep['candidate']) == prep['candidate_files']
    for name, digest in prep['source_files'].items():
        assert sha256(ROOT / name) == digest, name
    assert sha256(OUT / 'roots.jsonl') == prep['roots_sha256']


def student():
    path = OUT / 'student.json'
    assert not path.exists(), 'Preserve all earlier attempts'
    prep = json.loads((OUT / 'preparation.json').read_text())
    verify(prep)
    base = ROOT / prep['candidate']
    roots = [json.loads(line) for line in (OUT / 'roots.jsonl').read_text().splitlines()]
    assert len(roots) == 5 and sum(len(r['choices']) for r in roots) == 11
    result = dict(status='initializing', pid=os.getpid(), preparation_sha256=sha256(OUT / 'preparation.json'),
        records=[], leaves=[], attempts=[], limits=dict(branches=11, branch_nodes=500000, branch_seconds=8,
            endpoints=60, endpoint_nodes=100000, endpoint_seconds=2))
    save_json(path, result)
    try:
        stop_check()
        sys.path.insert(0, str(base.resolve()))
        tick = time.perf_counter()
        import chess
        import numpy as np

        import agent

        driver = sys.modules['engine.compiled_driver']
        arrays, core, decode = driver.arrays, driver.core, driver.decode
        assert Path(core.__file__).resolve() == (base / 'engine/compiled_core.py').resolve()
        result['init_seconds'] = time.perf_counter() - tick
        assert result['init_seconds'] <= 90
        search = agent._search
        search.policy = None
        leaves = {}

        def restore(row):
            board = chess.Board(row['start_fen'])
            for move in row['history']:
                board.push_uci(move)
            assert board.fen() == row['fen'] and board.is_valid()
            return board

        def terminal(board):
            # Match this engine's terminal rules, including present repetitions.
            return (board.is_checkmate() or board.is_stalemate() or board.is_insufficient_material()
                or board.halfmove_clock >= 100 or board.is_repetition(3))

        def history(board):
            past, replay = [], board.copy(stack=True)
            for _ in range(min(board.halfmove_clock, len(board.move_stack)) + 1):
                pieces, state = arrays(replay)
                past.append(core.position_hash(pieces, state))
                if not replay.move_stack:
                    break
                replay.pop()
            past.reverse()
            hashes = np.zeros(800, dtype=np.uint64)
            hashes[:len(past)] = past
            context = np.uint64(sum(map(int, past)) & ((1 << 64) - 1))
            return hashes, past, context

        def evaluate(board, root_white, depth, ply, nodes, seconds, credits):
            stop_check()
            for name in ['ttkey', 'ttcontext', 'ttdata', 'killers', 'history']:
                getattr(search, name).fill(0)
            pieces, state = arrays(board)
            saved_pieces, saved_state = pieces.copy(), state.copy()
            accumulator = core.build_accumulator(pieces, search.weights, search.bias)
            saved_accumulator = accumulator.copy()
            hashes, past, context = history(board)
            control = np.array([0, 0, nodes], dtype=np.int64)
            signatures_before = tuple(map(str, core.search.signatures))
            tick = time.perf_counter()
            score = core.search(pieces, state, depth, -31000, 31000, ply, 0,
                hashes, len(past), context, search.ttkey, search.ttcontext, search.ttdata,
                search.killers, search.history, control, tick + seconds, search.weights,
                search.bias, search.output, search.blend, search.conversion, search.reductions,
                accumulator, credits, 4, 0)
            elapsed = time.perf_counter() - tick
            restored = (np.array_equal(pieces, saved_pieces) and np.array_equal(state, saved_state)
                and np.array_equal(accumulator, saved_accumulator) and list(hashes[:len(past)]) == past)
            added_signatures = [s for s in map(str, core.search.signatures) if s not in signatures_before]
            within_bounds = int(control[0]) <= nodes and elapsed <= seconds + .25
            valid = restored and within_bounds and not added_signatures
            factor = 1 if board.turn == root_white else -1
            measured = dict(complete=valid and not bool(control[1]),
                score_root=int(score) * factor if valid and not control[1] else None,
                nodes=int(control[0]), seconds=elapsed)
            result['attempts'].append(dict(fen=board.fen(), depth=depth, ply=ply,
                limits=dict(nodes=nodes, seconds=seconds), interrupted=bool(control[1]),
                restored=bool(restored), within_bounds=within_bounds,
                signature_count_before=len(signatures_before), added_signatures=added_signatures,
                **measured))
            save_json(path, result)
            assert valid, 'Diagnostic dispatch, restoration or resource bound failed; raw attempt preserved'
            return measured, context

        def features(board, root_white):
            pieces, state = arrays(board)
            factor = 1 if board.turn == root_white else -1
            material_white = sum((1 if p.color else -1) * int(core.MG[p.piece_type]) for p in board.piece_map().values())
            phase = sum(int(core.PHASE[p.piece_type]) for p in board.piece_map().values())
            pressures, passers = {}, []
            for side in [chess.WHITE, chess.BLACK]:
                enemy = not side
                king = board.king(enemy)
                units, attackers = 0, 0
                for sq, piece in board.piece_map().items():
                    if piece.color != side:
                        continue
                    if piece.piece_type in [chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
                        hits = len(board.attacks(sq) & chess.SquareSet(chess.BB_KING_ATTACKS[king]))
                        if hits:
                            attackers += 1
                            units += hits * {chess.KNIGHT: 2, chess.BISHOP: 2, chess.ROOK: 3, chess.QUEEN: 5}[piece.piece_type]
                    if piece.piece_type == chess.PAWN:
                        f, rank = chess.square_file(sq), chess.square_rank(sq)
                        passed = not any(abs(chess.square_file(other) - f) <= 1
                            and (chess.square_rank(other) > rank if side else chess.square_rank(other) < rank)
                            for other in board.pieces(chess.PAWN, enemy))
                        if passed:
                            relative_rank = rank if side else 7 - rank
                            imbalance = bool(board.pieces(chess.QUEEN, enemy)) and not board.pieces(chess.QUEEN, side)
                            multiplier = 2 if phase <= 8 and imbalance else 5
                            passers.append(dict(square=chess.square_name(sq), white=side, relative_rank=relative_rank,
                                mg_bonus=2 * relative_rank**2, eg_bonus=multiplier * relative_rank**2,
                                defenders=[chess.square_name(s) for s in board.attackers(side, sq)],
                                attackers=[chess.square_name(s) for s in board.attackers(enemy, sq)],
                                enemy_king_distance=chess.square_distance(sq, king)))
                pressures['white' if side else 'black'] = dict(units=units, attackers=attackers,
                    bonus=min(250, 2 * units * units) if board.pieces(chess.QUEEN, side) and attackers >= 2 else 0)
            shelters = {}
            for side in [chess.WHITE, chess.BLACK]:
                king = board.king(side)
                own = board.pieces(chess.PAWN, side)
                enemy = board.pieces(chess.PAWN, not side)
                king_file, king_rank = chess.square_file(king), chess.square_rank(king)
                direction = 1 if side else -1
                shelters['white' if side else 'black'] = dict(
                    king=chess.square_name(king),
                    own_pawns_on_file=sum(chess.square_file(p) == king_file for p in own),
                    enemy_pawns_on_file=sum(chess.square_file(p) == king_file for p in enemy),
                    close_forward_pawns=[chess.square_name(p) for p in own
                        if abs(chess.square_file(p) - king_file) <= 1
                        and 0 < direction * (chess.square_rank(p) - king_rank) <= 2],
                    absolutely_pinned=[chess.square_name(p) for p, piece in board.piece_map().items()
                        if piece.color == side and piece.piece_type != chess.KING and board.is_pinned(side, p)])
            return dict(king_shelter=shelters, static_root=int(core.classical(pieces, state, search.conversion)) * factor,
                material_root=material_white * (1 if root_white else -1), phase=phase,
                king_pressure=pressures, passers=passers, in_check=board.is_check())

        def add_leaf(board, root, origin):
            key = json.dumps([root['id'], board.root().fen(), [m.uci() for m in board.move_stack]])
            if key not in leaves:
                leaves[key] = dict(id=f'leaf-{len(leaves)+1:02}', target=root['id'],
                    start_fen=board.root().fen(), history=[m.uci() for m in board.move_stack], fen=board.fen(),
                    root_white=restore(root).turn, terminal=terminal(board), origins=[],
                    **features(board, restore(root).turn))
            leaves[key]['origins'].append(origin)
            assert len(leaves) <= 60
            return leaves[key]['id']

        result['status'] = 'student-pv-traces'
        for root in roots:
            position = restore(root)
            for forced in root['choices']:
                board = position.copy(stack=True)
                board.push_uci(forced)
                analysis, context = evaluate(board, position.turn, 5, 1, 500000, 8, 2)
                record = dict(target=root['id'], forced=forced, depth=6, analysis=analysis)
                if analysis['complete']:
                    remaining, credits, pv, entries = 5, 2, [forced], []
                    stop = 'trace_length_limit'
                    for ply in range(1, 10):
                        if terminal(board):
                            stop = 'terminal'
                            break
                        if remaining >= 0 and board.is_check() and credits > 0:
                            remaining += 1
                            credits -= 1
                        if remaining <= 0:
                            stop = 'quiescence_reached'
                            break
                        p, s = arrays(board)
                        key = core.position_hash(p, s)
                        salt = (credits * 0x9e3779b97f4a7c15) & ((1 << 64) - 1)
                        quiet_salt = (10 * 0xd6e8feb86659fd93) & ((1 << 64) - 1)
                        tt_context = np.uint64(int(context) ^ salt ^ quiet_salt)
                        slot = int(key) & (len(search.ttkey) - 1)
                        entry = search.ttdata[slot]
                        if not (search.ttkey[slot] == key and search.ttcontext[slot] == tt_context
                                and entry[4] == board.halfmove_clock and entry[0] >= remaining and entry[2] == 0):
                            stop = 'missing_or_nonexact_transposition_entry'
                            break
                        move = decode(int(entry[3])) if entry[3] else None
                        if move not in board.legal_moves:
                            stop = 'missing_or_illegal_table_move'
                            break
                        entries.append(dict(ply=ply, remaining_depth=remaining, credits=credits,
                            stored_depth=int(entry[0]), stored_bound=int(entry[2]), uci=move.uci(), san=board.san(move)))
                        old_rights = board.castling_rights
                        board.push(move)
                        pv.append(move.uci())
                        p, s = arrays(board)
                        child_key = core.position_hash(p, s)
                        context = child_key if board.halfmove_clock == 0 or board.castling_rights != old_rights else np.uint64(
                            (int(context) + int(child_key)) & ((1 << 64) - 1))
                        remaining -= 1
                    leaf_id = add_leaf(board, root, dict(kind='student', forced=forced,
                        trace_stop=stop, extensions_left=credits, pv=pv))
                    record['trace'] = dict(pv=pv, entries=entries, stop=stop, leaf_id=leaf_id)
                result['records'].append(record)
                result['leaves'] = list(leaves.values())
                save_json(path, result)
        for root in roots:
            for budget, verification in zip([80000, 320000], root['verification'], strict=True):
                for branch in ['best', 'played']:
                    for prefix in [4, 8]:
                        pv = verification[branch]['pv'][:prefix]
                        board = restore(root)
                        for move in pv:
                            board.push_uci(move)
                        add_leaf(board, root, dict(kind='teacher-counterfactual', branch=branch,
                            budget=budget, requested_prefix=prefix, pv=pv))
        result['status'] = 'endpoint-quiescence'
        for leaf in leaves.values():
            board = restore(leaf)
            if not leaf['terminal']:
                # Local leaf diagnosis, not a fabricated continuation of the earlier PV.
                leaf['quiescence'], _ = evaluate(board, leaf['root_white'], 0, 0, 100000, 2, 0)
            result['leaves'] = list(leaves.values())
            save_json(path, result)
        verify(prep)
        assert len(result['records']) == 11 and len(result['leaves']) <= 60
        result['status'] = 'complete'
    except BaseException as error:
        result.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(path, result)


def teacher():
    import chess

    from scripts.improvement_audit import evaluate
    from scripts.magnus_benchmark import SF
    from scripts.overnight_capacity import wait_for_capacity
    from training.puzzle_verifier import Verifier

    path = OUT / 'teacher.json'
    assert not path.exists(), 'Preserve all endpoint analyses'
    source = json.loads((OUT / 'student.json').read_text())
    assert source['status'] == 'complete' and len(source['leaves']) <= 60
    report = dict(status='running', source_sha256=sha256(OUT / 'student.json'), teacher_sha256=sha256(SF),
        budgets=[80000, 320000], newly_requested_nodes=0, leaves=[], automatic_fitting=False)
    save_json(path, report)
    wait_for_capacity(OUT / 'stockfish-capacity.json')
    verifier = Verifier(SF)
    try:
        for leaf in source['leaves']:
            stop_check()
            board = chess.Board(leaf['start_fen'])
            for move in leaf['history']:
                board.push_uci(move)
            assert board.fen() == leaf['fen']
            item = dict(leaf)
            if not leaf['terminal']:
                values = []
                for budget in report['budgets']:
                    stop_check()
                    report['newly_requested_nodes'] += budget
                    assert report['newly_requested_nodes'] <= 24000000
                    save_json(path, report)
                    value = evaluate(verifier.engine, board, budget)
                    factor = 1 if board.turn == leaf['root_white'] else -1
                    value['cp_root'] = value['cp'] * factor if value['cp'] is not None else None
                    value['mate_root'] = value['mate'] * factor if value['mate'] is not None else None
                    values.append(value)
                item['teacher'] = values
                score = leaf.get('quiescence', {}).get('score_root')
                item['quiescence_minus_teacher_cp'] = [score - v['cp_root'] if score is not None and v['cp_root'] is not None
                    else None for v in values]
            report['leaves'].append(item)
            save_json(path, report)
        assert report['newly_requested_nodes'] <= 24000000
        verify(json.loads((OUT / 'preparation.json').read_text()))
        report['status'] = 'complete'
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        verifier.close()
        save_json(path, report)


def main():
    from scripts.improvement_king_coordination_gate import child
    from scripts.overnight_capacity import wait_for_capacity

    path = OUT / 'context.json'
    assert not path.exists() and not (OUT / 'student.json').exists() and not (OUT / 'teacher.json').exists()
    report = dict(status='running', pid=os.getpid(), completed=[])
    save_json(path, report)
    try:
        for stage in ['student', 'teacher']:
            stop_check()
            report['stage'] = stage
            save_json(path, report)
            wait_for_capacity(OUT / (stage + '-capacity.json'))
            child(['-X', 'utf8', '-m', 'scripts.competition_counterfactuals', '--mode', stage], OUT / (stage + '.log'), timeout=360)
            assert json.loads((OUT / (stage + '.json')).read_text())['status'] == 'complete'
            report['completed'].append(stage)
        report.update(status='complete', stage='awaiting_critique')
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(path, report)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--mode', choices=['student', 'teacher'])
    args = parser.parse_args()
    if args.mode:
        (student if args.mode == 'student' else teacher)()
    else:
        main()
