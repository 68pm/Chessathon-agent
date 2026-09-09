"""Freeze specific development roots from the completed saved-loss review."""

import json
from collections import Counter

from scripts.feedback_matches_windows import feedback_path
from scripts.overnight_geometry_trial import ROOT, digest, save
from scripts.overnight_value_labels import restore


def run():
    directory = ROOT / 'runs/improvement-loop-20260907/n9-dev-2400/rated-prototype'
    out = ROOT / 'runs/overnight-20260909/development-root-01'
    assert not out.exists()
    paths = list(feedback_path(directory).glob('postgame-feedback/reviews/games/*/review.json'))
    documents = [json.loads(p.read_text(encoding='utf-8')) for p in paths]
    selected = [(p, d) for p, d in zip(paths, documents, strict=True)
                if d['identity']['game']['source_game_id'] == '1']
    assert len(selected) == 1
    source, doc = selected[0]
    assert doc['status'] == 'complete' and len(doc['rows']) == 53
    roots = []
    for move_number, priority in ((23, 'first_confident_middlegame_error'), (33, 'already_losing_secondary_error')):
        row = next(r for r in doc['rows'] if r['fullmove'] == move_number)
        board = restore(row)
        roots.append(dict(priority=priority, **row))
        assert not board.is_game_over()
    first = roots[0]
    assert first['played'] == 'e3e4' and first['policy_target'] == 'f1f3'
    assert all(label['best']['pv'][0] == 'f1f3' for label in first['labels'])
    out.mkdir()
    save(out / 'targets.json', dict(status='complete', source_game=doc['identity']['game'],
        source_review=str(source.relative_to(feedback_path(ROOT))), source_sha256=digest(source),
        complete_move_counts=dict(Counter(r['tags'][0] for r in doc['rows'])),
        rewarded=doc['rewarded'], penalised=doc['penalised'], labels=doc['labels'], roots=roots,
        scope='Development diagnosis only. First completed loss retained exactly. No new search, teacher work, fitting or release promotion.',
        next_step='After active matches and feedback finish, examine move23 at its actual search budget. Compare Rf3 and e4 continuations. Independently label quiet descendants before any value learning; root reward is not a leaf value.',
        split_constraint='The entire D65 colour pair and descendants must stay together; no white/black train-validation split of this shared start.'))
    print(json.dumps(dict(status='complete', roots=len(roots), own_moves=53,
        rewarded=doc['rewarded'], penalised=doc['penalised'])))


if __name__ == '__main__':
    run()
