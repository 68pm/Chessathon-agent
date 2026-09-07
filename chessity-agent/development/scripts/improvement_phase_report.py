"""Locate first deterioration by phase, reusing complete verified move audits."""

import argparse
import json
from collections import Counter
from pathlib import Path

import chess

from scripts.alien_rating_ladder import save_json, sha256
from scripts.fastchess_matches import score_summary

PHASES = ('opening', 'middlegame', 'endgame')
WEIGHTS = {chess.KNIGHT: 1, chess.BISHOP: 1, chess.ROOK: 2, chess.QUEEN: 4}


def phase_details(board):
    material = sum(WEIGHTS.get(p.piece_type, 0) for p in board.piece_map().values())
    phase = 'endgame' if material <= 8 else 'opening' if board.fullmove_number <= 12 else 'middlegame'
    return dict(phase=phase, material_phase=material, fullmove=board.fullmove_number)


def finite_gap(pair):
    a, b = pair['best']['cp'], pair['played']['cp']
    return a - b if a is not None and b is not None else None


def at_least(score, threshold):
    return score['cp'] >= threshold if score['cp'] is not None else score['mate'] is not None and score['mate'] > 0


def at_most(score, threshold):
    return score['cp'] <= threshold if score['cp'] is not None else score['mate'] is not None and score['mate'] < 0


def error_signals(row):
    pairs = row['verification']
    if len(pairs) != 2:
        return dict(large_cp_error=False, losing_transition=False, mate_loss_transition=False,
                    squandered_advantage=False, mate_scored=False)
    gaps = [finite_gap(p) for p in pairs]
    mate_loss = all(p['played']['mate'] is not None and p['played']['mate'] < 0
                    and (p['best']['cp'] is not None or p['best']['mate'] is not None
                         and p['best']['mate'] > 0) for p in pairs)
    return dict(
        large_cp_error=all(g is not None and g >= 200 for g in gaps),
        losing_transition=all(at_least(p['best'], -199) and at_most(p['played'], -200)
                              and (g is None or g >= 80) for p, g in zip(pairs, gaps, strict=True)),
        mate_loss_transition=mate_loss,
        squandered_advantage=all(at_least(p['best'], 200) and at_most(p['played'], 100) for p in pairs),
        mate_scored=any(p[branch]['mate'] is not None for p in pairs for branch in ['best', 'played']))


def summarise(rows):
    groups = {}
    for opponent in sorted({g['opponent'] for g in rows}):
        games = [g for g in rows if g['opponent'] == opponent]
        losses = [g for g in games if g['score'] == 0]
        nonwins = [g for g in games if g['score'] < 1]
        def phases(items, key):
            counts = Counter(g[key]['phase'] if g[key] else 'unresolved' for g in items)
            return {p: counts[p] for p in (*PHASES, 'unresolved')}
        exposure = {phase: {key: sum(g['phase_exposure'][phase][key] for g in games)
                           for key in ['own_moves', 'large_cp_errors', 'mate_scored']} for phase in PHASES}
        for count in exposure.values():
            count['large_errors_per_100_observed_moves'] = 100 * count['large_cp_errors'] / count['own_moves'] if count['own_moves'] else None
        groups[opponent] = dict(games=len(games), wins=sum(g['score'] == 1 for g in games),
            draws=sum(g['score'] == .5 for g in games), losses=len(losses),
            loss_first_warning_phase=phases(losses, 'first_warning'),
            loss_first_losing_transition_phase=phases(losses, 'first_losing_transition'),
            loss_terminal_phase=dict(Counter(g['terminal']['phase'] for g in losses)),
            nonwin_first_squandered_advantage_phase=phases(nonwins, 'first_squandered_advantage'),
            phase_exposure=exposure)
    return groups


def report(matches, audit, out, label):
    if out.exists():
        raise ValueError('Preserve existing diagnosis; use a new output for a changed analysis.')
    source = json.loads(matches.read_text(encoding='utf-8'))
    check = json.loads((audit / 'audit.json').read_text(encoding='utf-8'))
    context = json.loads((audit / 'context.json').read_text(encoding='utf-8'))
    assert source['status'] == check['status'] == 'complete'
    assert len(source['games']) == len(source['schedule']) == check['games']
    assert check['context'] == context and context['source_sha256'] == sha256(matches)
    assert context['verify_nodes'] == [80000, 320000]
    candidates = {g['candidate_path'] for g in source['games']}
    assert len(candidates) == 1
    rows = [json.loads(line) for line in (audit / 'positions.jsonl').read_text(encoding='utf-8').splitlines()]
    indexed = {r['id']: r for r in rows}
    assert len(indexed) == len(rows) == check['own_moves']
    used, games, targets = set(), [], []
    for game in sorted(source['games'], key=lambda g: g['id']):
        start = chess.Board(game.get('start_fen', chess.STARTING_FEN))
        for uci in game['opening']:
            start.push_uci(uci)
        board = chess.Board(start.fen())
        records = []
        counts = {p: dict(own_moves=0, large_cp_errors=0, mate_scored=0) for p in PHASES}
        for ply, move in enumerate(game['moves']):
            assert board.fen() == move['fen'] and board.turn == move['white']
            if move['white'] == game['candidate_white']:
                uid = f"game-{game['id']:03}-ply-{ply:03}"
                row = indexed[uid]
                assert row['game_id'] == game['id'] and row['game_score'] == game['score']
                assert row['opponent'] == game['family'] and row['played'] == move['uci']
                assert row['fen'] == board.fen() and row['clock_ms'] == move['clock_before_ms']
                assert row['start_fen'] == board.root().fen()
                assert row['history'] == [m.uci() for m in board.move_stack]
                used.add(uid)
                signals = error_signals(row)
                details = phase_details(board)
                count = counts[details['phase']]
                count['own_moves'] += 1
                count['large_cp_errors'] += int(signals['large_cp_error'])
                count['mate_scored'] += int(signals['mate_scored'])
                records.append(dict(id=uid, game_ply=ply, **details, **signals,
                    fen=row['fen'], played=row['played'], clock_ms=row['clock_ms'],
                    alternative_by_budget=[p['best']['pv'][0] for p in row['verification']],
                    verification=row['verification'], start_fen=row['start_fen'], history=row['history']))
            board.push_uci(move['uci'])
        assert board.fen() == game['final_fen']
        def first(*signals):
            return next((r for r in records if any(r[s] for s in signals)), None)
        result = dict(id=game['id'], opponent=game['family'], score=game['score'],
            candidate_white=game['candidate_white'], termination=game['termination'],
            terminal=phase_details(board), phase_exposure=counts,
            first_warning=first('large_cp_error', 'losing_transition', 'mate_loss_transition'),
            first_large_error=first('large_cp_error'), first_losing_transition=first('losing_transition'),
            first_mate_loss_transition=first('mate_loss_transition'),
            first_squandered_advantage=first('squandered_advantage'))
        games.append(result)
        if game['score'] < 1:
            chosen = {r['id']: r for r in [result['first_warning'], result['first_losing_transition'],
                                          result['first_squandered_advantage']] if r}
            for uid, row in chosen.items():
                targets.append(dict(source_id=f'{label}:{uid}', source_game_id=f'{label}:{game["id"]}',
                    opponent=game['family'], score=game['score'], opening=game['opening'],
                    split='development_review_queue', acceptance='Not yet accepted for fitting; successor stability and partition checks remain required.',
                    **row))
    assert used == set(indexed)
    result = dict(status='complete', label=label, candidate=next(iter(candidates)),
        matches_sha256=sha256(matches), audit_sha256=sha256(audit / 'positions.jsonl'),
        source_code_sha256=sha256(__file__), teacher_context=context, new_teacher_nodes=0,
        definitions=dict(endgame_material_phase_max=8, opening_fullmove_max=12,
            material_weights={chess.piece_name(p): w for p, w in WEIGHTS.items()},
            verified_large_error_cp=200, losing_cutoff_cp=-200, minimum_finite_crossing_gap_cp=80,
            squandered_best_min_cp=200, squandered_played_max_cp=100),
        match_summary=score_summary(source['games']), groups=summarise(games), games=games,
        review_queue=targets, total_verified_large_errors=sum(c['large_cp_errors'] for g in games for c in g['phase_exposure'].values()),
        scope='Operational phases; first verified warning is not proof of the cause of a loss. Screening can miss errors. Mate uncertainty and losses without warnings retained. Candidate/opponent groups stay separate. Exposed development data, no Elo or consistency inference, no new accepted training labels.')
    assert result['total_verified_large_errors'] == check['large_errors']
    out.parent.mkdir(parents=True, exist_ok=True)
    save_json(out, result)
    print(json.dumps(dict(label=label, groups=result['groups'], queued=len(targets), new_teacher_nodes=0)), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--matches', required=True, type=Path)
    parser.add_argument('--audit', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    report(args.matches, args.audit, args.out, args.label)
