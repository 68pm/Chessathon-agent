"""Describe existing verified refutations without JIT, searches or training."""
import json
import time
from pathlib import Path

from scripts.alien_rating_ladder import save_json, sha256

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT / 'runs/improvement-loop-20260907/cycle-28'
    path = out / 'refutation-features.json'
    if path.exists():
        raise ValueError('Preserve completed descriptive analysis')
    from scripts.overnight_capacity import wait_for_capacity

    wait_for_capacity(out / 'capacity.json')
    started = time.perf_counter()
    import chess

    from experiments import queen_check_core as core
    from experiments.aspiration_driver import arrays

    roots_path = ROOT / 'runs/improvement-loop-20260907/cycle-20/roots.jsonl'
    cache_path = ROOT / 'runs/improvement-loop-20260907/cycle-23-credit-checks/choice-cache.jsonl'
    target = next(r for r in map(json.loads, roots_path.read_text().splitlines())
                  if r['id'] == 'startup19-game-003-ply-068')
    cached = {r['key']:r['analysis'] for r in map(json.loads, cache_path.read_text().splitlines())}
    assert not core.classical.signatures
    report = dict(status='running', target=target, roots_sha256=sha256(roots_path),
        cache_sha256=sha256(cache_path), core_sha256=sha256(core.__file__), source_sha256=sha256(__file__),
        plan_sha256=sha256(ROOT / 'docs/IMPROVEMENT_CYCLE_28.md'), lines=[], new_teacher_nodes=0,
        maximum_positions=264, maximum_plies_per_line=32,
        scope='Descriptive existing-PV features; root teacher scores are NOT labels for every descendant.')
    save_json(path, report)

    def features(board):
        pieces, state = arrays(board)
        factor = 1 if board.turn else -1
        static_white = int(core.classical.py_func(pieces, state, False)) * factor
        phase = min(24, sum(int(core.PHASE[p.piece_type]) for p in board.piece_map().values()))
        material = sum((1 if p.color else -1) * int(core.MG[p.piece_type]) for p in board.piece_map().values())
        danger = {}
        weights = {chess.PAWN:1, chess.KNIGHT:2, chess.BISHOP:2, chess.ROOK:3, chess.QUEEN:5, chess.KING:0}
        for colour in chess.COLORS:
            king = board.king(colour)
            ring = chess.SquareSet(chess.BB_KING_ATTACKS[king])
            attacked, attackers, units, legacy_pressure = set(), set(), 0, 0
            for square, piece in board.piece_map().items():
                if piece.color == colour:
                    continue
                hits = set(board.attacks(square) & ring)
                attacked.update(hits)
                if hits and piece.piece_type != chess.KING:
                    attackers.add(square)
                    units += weights[piece.piece_type] * len(hits)
                if piece.piece_type not in [chess.PAWN, chess.KING]:
                    legacy_pressure += len(hits) * (7 if piece.piece_type in [chess.KNIGHT, chess.BISHOP] else 5)
            queens = board.pieces(chess.QUEEN, not colour)
            danger['white' if colour else 'black'] = dict(
                king=chess.square_name(king), attacked_ring_squares=len(attacked),
                nonking_attackers=len(attackers), weighted_attack_units=units,
                existing_tapered_pressure_cp=legacy_pressure * phase / 24,
                enemy_queen_distance=min(chess.square_distance(king, q) for q in queens) if queens else None,
                enemy_queen_count=len(queens))
        return dict(fen=board.fen(), classical_white_cp=static_white, material_white_cp=material,
                    phase=phase, king_features=danger)

    try:
        for forced in ['d8c8', 'd8d3', 'c3d1', 'c3d5']:
            for index, budget in enumerate([80000, 320000]):
                if any((ROOT / flag).exists() for flag in ['STOP_TRAINING', 'STOP_BENCHMARK']):
                    raise InterruptedError('User stop flag')
                reference = target['verification'][index]
                key = f'{target["id"]}:{forced}:{budget}'
                if forced == target['played']:
                    analysis = reference['played']
                elif forced == reference['best']['pv'][0]:
                    analysis = reference['best']
                else:
                    analysis = cached[key]
                assert analysis['pv'][0] == forced
                board = chess.Board(target['start_fen'])
                for uci in target['history']:
                    board.push_uci(uci)
                assert board.fen() == target['fen'] and board.is_valid()
                line = dict(forced=forced, budget=budget, root_analysis=analysis,
                            positions=[dict(ply=0, **features(board))])
                for ply, uci in enumerate(analysis['pv'][:32], 1):
                    move = chess.Move.from_uci(uci)
                    assert move in board.legal_moves
                    san = board.san(move)
                    board.push(move)
                    line['positions'].append(dict(ply=ply, uci=uci, san=san, **features(board)))
                report['lines'].append(line)
                save_json(path, report)
        assert len(report['lines']) == 8 and sum(len(trace['positions']) for trace in report['lines']) <= 264
        assert not core.classical.signatures
        report.update(status='complete', seconds=time.perf_counter() - started,
                      positions=sum(len(trace['positions']) for trace in report['lines']), jit_compilations=0)
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(path, report)
    print(json.dumps(dict(status=report['status'], positions=report['positions'], seconds=report['seconds'],
                         new_teacher_nodes=0, jit_compilations=0)))


if __name__ == '__main__':
    main()
