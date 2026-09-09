"""Trace the latest local errors and independently label their continuations."""
import argparse
import json
from pathlib import Path
from scripts import continuation_descendants as trace
from scripts.progression_common import ROOT, RUN, BASE, check_stop, digest, manifest, save

OUT = RUN / 'loss-descendants-01'


def prepare():
    from scripts.overnight_archive_challenge import archive_matches
    check_stop()
    assert not OUT.exists()
    archive_matches(ROOT.parent / 'chessity-agent-v1.56.zip', BASE)
    previous = ROOT / 'runs/evening-20260909/development-targets.json'
    rows = json.loads(previous.read_text())['rows']
    wanted = [('versus56-b12-game-2', 9), ('versus56-b12-game-2', 21),
        ('versus56-b12-game-2', 35), ('versus56-d48-game-1', 30),
        ('versus56-d48-game-2', 17)]
    roots = []
    for game, move in wanted:
        found = [r for r in rows if r['game'] == game and r['fullmove'] == move]
        assert len(found) == 1 and found[0]['policy_target']
        row = dict(found[0], id=f'{game}-move{move}')
        trace.restore(row)
        roots.append(row)
    from scripts.feedback_matches_windows import feedback_path
    from training.game_feedback import normalise_game
    latest = ROOT / 'runs/improvement-loop-20260907/p9-v156-development2400-01/rated-prototype'
    game = json.loads((latest / 'game-001.json').read_text())
    assert game['candidate_white'] and game['candidate_path'] == str(BASE.relative_to(ROOT))
    _, identity = normalise_game(game)
    feedback = feedback_path(latest / 'postgame-feedback')
    marker = json.loads((feedback / 'completed' / (identity['game_key'] + '.json')).read_text())
    review_path = feedback / marker['review']
    review = json.loads(review_path.read_text())
    assert review['status'] == 'complete'
    found = [r for r in review['rows'] if r['fullmove'] == 35]
    assert len(found) == 1 and found[0]['policy_target'] == 'g4g5'
    row = dict(found[0], id='v156-development2400-white-move35', source_game_key=identity['game_key'])
    trace.restore(row); roots.append(row)
    selected = json.loads((ROOT.parent / 'chessity-agent-version.json').read_text())
    assert selected['version'] == 'v1.56'
    OUT.mkdir(parents=True)
    sources = [Path(__file__), Path(trace.__file__), previous,
        ROOT / 'scripts/progression_common.py', ROOT / 'training/game_feedback.py', review_path]
    save(OUT / 'preparation.json', dict(candidate=str(BASE.relative_to(ROOT)), files=manifest(BASE),
        selected_version=selected['version'], selected_sha256=selected['sha256'], roots=roots,
        sources={str(p): digest(p) for p in sources}, child_depth=7, branch_nodes=2000000,
        branch_seconds=5., quiescence_nodes=100000, quiescence_seconds=2., max_leaves=72,
        teacher_budgets=[80000, 320000], max_teacher_nodes=28800000,
        scope='Five earlier challenger errors plus the new v1.56 35.h5 loss; frozen v1.56 continuations and independently evaluated '
              'counterfactual leaves. No copying root rewards into static values; no fitting or promotion.'))
    print('Prepared six loss roots for independent descendant labelling', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=('prepare', 'student', 'teacher'), required=True)
    args = parser.parse_args()
    trace.OUT, trace.check_stop = OUT, check_stop
    {'prepare': prepare, 'student': trace.student, 'teacher': trace.teacher}[args.mode]()
