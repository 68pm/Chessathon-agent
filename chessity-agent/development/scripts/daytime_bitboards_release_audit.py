"""Audit a finished, qualifying pawn candidate screen before any release mutation."""

import json
from collections import Counter
from datetime import datetime, timezone

from scripts.daytime_common import ROOT, RUN, digest, manifest, save
from scripts.daytime_pawn_bitboards_screen import pair_passes, qualifies_2800
from scripts.feedback_matches_windows import feedback_path
from scripts.overnight_archive_challenge import archive_matches
from scripts.overnight_portable_fast_screen import audit_feedback
from training.game_feedback import normalise_game

OUT = RUN / 'pawn-bitboards-release-audit-01'


def summary(games):
    return dict(games=len(games), wins=sum(g['score'] == 1 for g in games),
        draws=sum(g['score'] == .5 for g in games), losses=sum(g['score'] == 0 for g in games),
        terminations=dict(Counter(g['termination'] for g in games)),
        operational_games=sum(g.get('failed_colour') is not None or g['termination'] in
            ('flag','illegal','crash','init','both_failed') for g in games))


def run():
    from scripts.daytime_pawn_bitboards_screen import operationally_clean

    assert not OUT.exists()
    screen = RUN / 'pawn-bitboards-screen-01'
    prep = json.loads((screen / 'preparation.json').read_text())
    state = json.loads((screen / 'state.json').read_text())
    assert state['status'] == 'complete' and state['passed'] and state['frozen_candidates']
    assert all(r['status'] == 'complete' for r in state['stages'])
    assert all(manifest(ROOT / p) == h for p,h in prep['files'].items())
    assert all(digest(ROOT / p) == h for p,h in prep['source_sha256'].items())
    package = screen / 'pawn-bitboards-candidate.zip'
    assert digest(package) == prep['package_sha256'] == '29b322dba4ea61d0fce1709327810e8f9f199df79cf40cc92290ddf9ec083fc1'
    archive_matches(package, ROOT / prep['candidate'])
    validation = json.loads((screen / 'validation.json').read_text())
    assert validation['status'] == 'complete' and validation['sha256'] == prep['package_sha256']
    assert validation['init_ms'] < 90000 and validation['legal_calls'] == 2
    assert all(v == 'blocked' for v in validation['read_only_checks'].values())
    games, reviews, sources = {}, [], {}
    for item in state['matches']:
        path = ROOT / item['result_path']
        assert digest(path) == item['sha256']
        report = audit_feedback(path)
        games[item['label']] = report['games']
        assert operationally_clean(report['games'])
        sources[str(path.relative_to(ROOT))] = digest(path)
        feedback = feedback_path(path.parent / 'postgame-feedback')
        for game in report['games']:
            _, identity = normalise_game(game)
            marker = json.loads((feedback / 'completed' / (identity['game_key'] + '.json')).read_text())
            review = json.loads((feedback / marker['review']).read_text())
            reviews.append(dict(match=item['label'], game_key=identity['game_key'],
                own_moves=review['own_moves'], rewarded=review['rewarded'], penalised=review['penalised']))
    assert {'versus54','versus53','rated2400','rated2600'} <= games.keys()
    assert pair_passes(games['versus54'], 1.5) and pair_passes(games['versus53'], 1)
    assert ('rated2800' in games) == qualifies_2800(games['rated2600'])
    assert all(len(group) == 2 and {g['candidate_white'] for g in group} == {True, False} for group in games.values())
    for path in (screen/'state.json',screen/'preparation.json',screen/'validation.json',
                 RUN/'pawn-bitboards-01/state.json',RUN/'pawn-bitboards-quality-01/state.json'):
        sources[str(path.relative_to(ROOT))] = digest(path)
    highest = max((int(label.removeprefix('rated')) for label, group in games.items()
        if label.startswith('rated') and any(g['score'] == 1 for g in group)), default=None)
    result = dict(status='complete', eligible=True, completed_utc=datetime.now(timezone.utc).isoformat(),
        candidate=prep['candidate'], package=str(package.relative_to(ROOT)), sha256=digest(package),
        source_sha256=sources, files=prep['files'], groups={label:summary(group) for label,group in games.items()},
        reviews=reviews, reviewed_moves=sum(r['own_moves'] for r in reviews),
        positive_labels=sum(r['rewarded'] for r in reviews), negative_labels=sum(r['penalised'] for r in reviews),
        highest_nominal_win=highest, calibrated_elo=None, validation=validation,
        scope='Small exposed development screen; no independent or site Elo calibration. Existing policy unchanged; no new value fit included.',
        site_submission='not performed or verified by this audit')
    save(OUT/'audit.json',result)
    print(json.dumps({k:result[k] for k in ('status','eligible','groups','reviewed_moves','highest_nominal_win')}))


if __name__ == '__main__':
    run()
