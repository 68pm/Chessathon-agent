"""Prepare one held-out source group of independently labelled diagnostic descendants."""

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

from scripts import overnight_value_labels as labeler
from scripts.feedback_matches_windows import feedback_path
from scripts.overnight_geometry_trial import ROOT, digest, save

OUT = ROOT / 'runs/overnight-20260909/development-values-01'


def prepare():
    assert not OUT.exists(), 'Preserve prior preparations.'
    directory = ROOT / 'runs/improvement-loop-20260907/n9-dev-2400/rated-prototype'
    from scripts.overnight_portable_screen import audit_feedback
    match = audit_feedback(directory / 'results.json')
    assert len(match['games']) == 2 and [g['score'] for g in match['games']] == [0., .5]
    sources = sorted(feedback_path(directory).glob('postgame-feedback/reviews/games/*/review.json'))
    docs = [json.loads(p.read_text(encoding='utf-8')) for p in sources]
    assert len(docs) == 2 and all(d['status'] == 'complete' for d in docs)
    starts = {d['identity']['game']['start_fen'] for d in docs}
    assert len(starts) == 1
    group = hashlib.sha256(next(iter(starts)).encode()).hexdigest()
    previous = ROOT / 'runs/overnight-20260909/value-labels-02/preparation.json'
    old_targets = json.loads(previous.read_text(encoding='utf-8'))['targets']
    seen = {r['duplicate_key'] for r in old_targets}
    selected = {'1': [23, 33], '2': [13, 25, 26, 30, 31, 35, 39, 41]}
    targets, exclusions, root_summary = [], [], []
    for source, doc in zip(sources, docs, strict=True):
        game = doc['identity']['game']
        for number in selected[game['source_game_id']]:
            root = next(r for r in doc['rows'] if r['fullmove'] == number)
            board = labeler.restore(root)
            import chess
            target_san = board.san(chess.Move.from_uci(root['policy_target'])) if root['policy_target'] else None
            root_summary.append(dict(game=game['source_game_id'], fullmove=number, played=root['san'],
                target_san=target_san, regret_cp=root['regret_cp'], phase=root['tags'][0],
                best_cp=[v['best']['cp'] for v in root['labels']], played_cp=[v['played']['cp'] for v in root['labels']]))
            for branch in ('best', 'played'):
                board = labeler.restore(root)
                for depth, uci in enumerate(root['labels'][-1][branch]['pv'][:4], 1):
                    board.push_uci(uci)
                    if depth not in (2, 4):
                        continue
                    key = labeler.duplicate(board)
                    if (board.is_check() or board.is_game_over(claim_draw=True) or
                            board.is_repetition(2) or board.halfmove_clock >= 70 or key in seen):
                        exclusions.append(dict(game=game['source_game_id'], fullmove=number,
                            branch=branch, depth=depth, reason='check/terminal/repetition/draw-clock/duplicate-or-prior-target'))
                        continue
                    seen.add(key)
                    history = [m.uci() for m in board.move_stack]
                    identity = hashlib.sha256(json.dumps([game['game_key'], root['ply'], branch, depth, history]).encode()).hexdigest()
                    targets.append(dict(id=identity, source=str(source.relative_to(feedback_path(ROOT))),
                        source_game_id=game['source_game_id'], game_key=game['game_key'], group=group,
                        split='validation', root_ply=root['ply'], branch=branch, descendant_plies=depth,
                        start_fen=board.root().fen(), history=history, fen=board.fen(), duplicate_key=key,
                        original_move_reward=root['reward'],
                        note='Held out from value fitting as a complete D65 group. Root reward is provenance only; requires independent value labels. Development diagnosis, not independent playing-strength evidence.'))
    assert 8 <= len(targets) <= 40
    out_sources = {str(p.relative_to(feedback_path(ROOT))): digest(p) for p in sources}
    out_sources.update({str(p.relative_to(ROOT)): digest(p) for p in (
        Path(__file__), Path(labeler.__file__), previous,
        ROOT / 'scripts/feedback_matches_windows.py', ROOT / 'scripts/overnight_portable_screen.py',
        ROOT / 'docs/OVERNIGHT_PAIR_VALUE_TARGETS_20260909.md')})
    OUT.mkdir()
    save(OUT / 'preparation.json', dict(source_sha256=out_sources, targets=targets,
        group=group, split='validation', exclusions=exclusions, root_summary=root_summary,
        phase_counts=dict(Counter(r['tags'][0] for d in docs for r in d['rows'])),
        rewarded=sum(d['rewarded'] for d in docs), penalised=sum(d['penalised'] for d in docs),
        max_teacher_nodes=len(targets) * 400000,
        scope='Diagnostic descendants from the completed D65 pair; whole group reserved from position-value fitting. No new model, promotion or calibrated Elo. Existing broad-data collisions must also be checked before any future fit uses this holdout.'))
    print(json.dumps(dict(targets=len(targets), max_teacher_nodes=len(targets) * 400000, groups=1, split='validation')))


def run():
    previous = labeler.OUT
    try:
        labeler.OUT = OUT
        labeler.run()
    finally:
        labeler.OUT = previous


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    prepare() if parser.parse_args().prepare else run()
