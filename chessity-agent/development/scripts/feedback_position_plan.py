"""Plan a small descendant curriculum from completed reviews without running engines."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import chess

from scripts.feedback_matches_windows import feedback_path
from scripts.overnight_geometry_trial import ROOT, digest, save
from scripts.overnight_value_labels import duplicate, restore
from training.game_feedback import grade, phase

PRIOR_INPUTS = (
    'runs/overnight-20260909/value-labels-02/preparation.json',
    'runs/overnight-20260909/development-values-01/preparation.json',
    'runs/overnight-20260909/rule-value-01/preparation.json',
)


def finite_scores(row):
    labels = row.get('labels', [])
    return (len(labels) == 2 and all(v['mate'] is None and v['cp'] is not None
        for label in labels for v in (label['best'], label['played'])))


def choose_roots(rows):
    """Prioritize recoverable mistakes, then retain two examples of good play."""
    negatives = [r for r in rows if (r.get('reward') or 0) < 0 and
                 r.get('policy_target') and finite_scores(r)]
    recoverable = [r for r in negatives if min(v['best']['cp'] for v in r['labels']) >= -300]
    chosen, used = [], set()

    def add(row, reason):
        if row and row['ply'] not in used:
            chosen.append((row, reason))
            used.add(row['ply'])

    add(min(recoverable, key=lambda r: r['ply'], default=None), 'first_recoverable_error')
    add(max(recoverable, key=lambda r: (min(r['regret_cp']), -r['ply']), default=None),
        'largest_recoverable_error')
    conversions = [r for r in recoverable if min(v['best']['cp'] for v in r['labels']) >= 150]
    add(min(conversions, key=lambda r: r['ply'], default=None), 'missed_advantage_conversion')
    for row in sorted(recoverable, key=lambda r: (-min(r['regret_cp']), r['ply'])):
        if len(chosen) >= 3:
            break
        add(row, 'additional_recoverable_error')
    positives = [r for r in rows if (r.get('reward') or 0) > 0 and
                 r.get('policy_target') == r['played'] and finite_scores(r)]
    positive_count = 0
    for stage in ('middlegame', 'endgame', 'opening'):
        pool = [r for r in positives if r['tags'][0] == stage]
        advantages = [r for r in pool if 'preserves_estimated_advantage' in r['tags']]
        pool = advantages or pool
        if pool:
            pool.sort(key=lambda r: r['ply'])
            add(pool[len(pool) // 2], 'supported_good_move_' + stage)
            positive_count += 1
        if positive_count == 2:
            break
    return chosen


def validate_review(doc):
    assert doc['status'] == 'complete', 'Only completed immutable reviews are usable.'
    game = doc['identity']['game']
    assert len(doc['rows']) == doc['own_moves']
    assert len({r['ply'] for r in doc['rows']}) == len(doc['rows'])
    initial_turn = chess.Board(game['start_fen']).turn
    expected_plies = [i for i in range(len(game['moves']))
                      if (initial_turn if i % 2 == 0 else not initial_turn) == game['candidate_white']]
    assert [r['ply'] for r in doc['rows']] == expected_plies, 'Missing or reordered own moves.'
    for row in doc['rows']:
        assert row['start_fen'] == game['start_fen']
        assert [v['nodes'] for v in row['labels']] == [80000, 320000]
        board = restore(row)
        assert row['history'] == game['moves'][:row['ply']]
        assert row['played'] == game['moves'][row['ply']]
        assert board.turn == game['candidate_white'] == row['white']
        assert row['san'] == board.san(chess.Move.from_uci(row['played']))
        computed = grade(row['labels'], row['played'], board.legal_moves.count())
        assert computed['reward'] == row['reward'] and computed['label'] == row['label']
        if row.get('policy_target'):
            assert row['policy_target'] == computed['policy_target']


def start_group(game):
    return hashlib.sha256(duplicate(chess.Board(game['start_fen'])).encode()).hexdigest()


def plan(documents, previous_keys=()):
    assert documents and len({d['identity']['game']['game_key'] for _, d in documents}) == len(documents)
    for _, doc in documents:
        validate_review(doc)
    groups = {start_group(d['identity']['game']) for _, d in documents}
    # Allocate before any endpoint labels. Games sharing a start never split.
    ordered = sorted(groups, key=lambda g: hashlib.sha256(('20260909-feedback-plan:' + g).encode()).hexdigest())
    heldout = set(ordered[:max(1, (len(groups) + 4) // 5)])
    summaries, planned, exclusions = [], [], []
    previous_keys = set(previous_keys)
    for source, doc in documents:
        game = doc['identity']['game']
        group = start_group(game)
        split = 'validation' if group in heldout else 'train'
        chosen = choose_roots(doc['rows'])
        stages = {}
        for stage in ('opening', 'middlegame', 'endgame'):
            rows = [r for r in doc['rows'] if r['tags'][0] == stage]
            negatives = [r for r in rows if (r.get('reward') or 0) < 0]
            stages[stage] = dict(moves=len(rows), positive=sum((r.get('reward') or 0) > 0 for r in rows),
                negative=len(negatives), earliest_negative_ply=min((r['ply'] for r in negatives), default=None),
                recoverable_negative=sum(finite_scores(r) and min(v['best']['cp'] for v in r['labels']) >= -300 for r in negatives))
        roots = []
        for row, reason in chosen:
            board = restore(row)
            roots.append(dict(ply=row['ply'], fullmove=row['fullmove'], played=row['san'],
                target=board.san(chess.Move.from_uci(row['policy_target'])), reason=reason,
                phase=phase(board), regret_cp=row['regret_cp'], reward=row['reward'],
                best_cp=[v['best']['cp'] for v in row['labels']]))
            active_root = board.fullmove_number > 12
            for branch in ('best', 'played'):
                board = restore(row)
                for depth, uci in enumerate(row['labels'][-1][branch]['pv'][:4], 1):
                    board.push_uci(uci)
                    if depth not in (2, 4):
                        continue
                    key = duplicate(board)
                    reason_excluded = ('check' if board.is_check() else
                        'terminal_or_draw_claim' if board.is_game_over(claim_draw=True) else
                        'repetition' if board.is_repetition(2) else
                        'draw_clock' if board.halfmove_clock >= 70 else
                        'prior_label_or_model_training_collision' if key in previous_keys else None)
                    if reason_excluded:
                        exclusions.append(dict(game_key=game['game_key'], root_ply=row['ply'],
                            branch=branch, depth=depth, reason=reason_excluded))
                        continue
                    history = [m.uci() for m in board.move_stack]
                    identity = hashlib.sha256(json.dumps([game['game_key'], row['ply'], branch, depth, history]).encode()).hexdigest()
                    planned.append(dict(id=identity, source=source, game_key=game['game_key'],
                        source_game_id=game['source_game_id'], candidate_version=game['candidate_version'],
                        group=group, split=split, root_ply=row['ply'], branch=branch,
                        descendant_plies=depth, start_fen=board.root().fen(), history=history,
                        fen=board.fen(), duplicate_key=key, original_move_reward=row['reward'],
                        selection_reason=reason, phase=phase(board),
                        guarded_residual_active=active_root and phase(board) == 'middlegame',
                        target_stm_cp=None,
                        note='Root reward is provenance only. Independent endpoint labels are required; no fitting or runtime update has occurred.'))
        summaries.append(dict(game_key=game['game_key'], source_game_id=game['source_game_id'],
            candidate_version=game['candidate_version'], opponent=game['opponent'],
            score=game['score'], group=group, split=split, phase_counts=stages, selected_roots=roots))
    kept, seen = [], set()
    for row in sorted(planned, key=lambda r: (r['split'] != 'validation', r['id'])):
        if row['duplicate_key'] in seen:
            exclusions.append(dict(id=row['id'], reason='duplicate_or_mirror_validation_priority'))
            continue
        seen.add(row['duplicate_key'])
        kept.append(row)
    assert len(kept) <= 20 * len(documents)
    return dict(status='prepared', groups=sorted(groups), heldout_groups=sorted(heldout),
        targets=kept, summaries=summaries, exclusions=exclusions,
        maximum_teacher_nodes=len(kept) * 400000,
        phase_counts=dict(Counter(r['phase'] for r in kept)),
        residual_active_targets=sum(r['guarded_residual_active'] for r in kept),
        scope='Fixed bounded curriculum from complete reviews. No teacher work, training, candidate mutation or rating estimate. Prior collision exclusions protect a later independent value diagnostic; these games are already development data.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviews', type=Path, nargs='+', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    out = args.out.resolve()
    assert out.is_relative_to(ROOT / 'runs/overnight-20260909') and not out.exists()
    paths = [feedback_path(p.resolve()) for p in args.reviews]
    documents = [(str(p.relative_to(feedback_path(ROOT))), json.loads(p.read_text(encoding='utf-8'))) for p in paths]
    prior = [ROOT / p for p in PRIOR_INPUTS]
    previous = set()
    for path in prior:
        doc = json.loads(path.read_text(encoding='utf-8'))
        previous.update(r.get('duplicate_key', r.get('key')) for r in doc.get('targets', doc.get('rows', [])))
    previous.discard(None)
    result = plan(documents, previous)
    sources = [*paths, *map(feedback_path, prior), feedback_path(Path(__file__)),
        feedback_path(ROOT / 'docs/OVERNIGHT_FEEDBACK_POSITION_PLAN_20260909.md'),
        feedback_path(ROOT / 'tests/test_feedback_position_plan.py'),
        feedback_path(ROOT / 'scripts/overnight_value_labels.py'),
        feedback_path(ROOT / 'training/game_feedback.py')]
    result['source_sha256'] = {str(p.relative_to(feedback_path(ROOT))): digest(p) for p in sources}
    out.mkdir()
    save(out / 'preparation.json', result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('source_sha256', 'targets', 'summaries', 'exclusions')}))


if __name__ == '__main__':
    main()
