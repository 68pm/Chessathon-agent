"""Review exact-version challenge evidence without promoting or running engines."""

import json
from pathlib import Path

from scripts.feedback_matches_windows import feedback_path
from scripts.feedback_position_plan import validate_review
from scripts.feedback_screen_review import summarize
from scripts.overnight_archive_challenge import ARCHIVE, CHALLENGER, OUT, SELECTED, archive_matches
from scripts.overnight_geometry_trial import ROOT, digest, manifest, save
from scripts.overnight_portable_fast_screen import advance, audit_feedback, clean_win
from training.game_feedback import normalise_game


def collect(result_path):
    path = feedback_path(result_path)
    result = audit_feedback(path)
    feedback = []
    hashes = {str(path.relative_to(feedback_path(ROOT))):digest(path)}
    for game in result['games']:
        _, identity = normalise_game(game)
        directory = path.parent / 'postgame-feedback'
        marker = json.loads((directory / 'completed' / (identity['game_key'] + '.json')).read_text(encoding='utf-8'))
        review_path, fit_path = directory / marker['review'], directory / marker['training']
        doc = json.loads(review_path.read_text(encoding='utf-8'))
        fit = json.loads(fit_path.read_text(encoding='utf-8'))
        validate_review(doc)
        assert doc['identity']['game'] == identity and fit['status'] == 'complete'
        assert digest(fit_path) == marker['training_sha256']
        hashes.update({str(p.relative_to(feedback_path(ROOT))):digest(p) for p in (review_path, fit_path)})
        feedback.append(dict(game_id=game['id'], game_key=identity['game_key'], family=game['family'],
            candidate_white=game['candidate_white'], score=game['score'], own_moves=doc['own_moves'],
            rewarded=doc['rewarded'], penalised=doc['penalised'], labels=doc['labels'],
            experimental_examples=fit['examples'], experimental_updates=fit['updates']))
    return result['games'], feedback, hashes


def run():
    out = OUT / 'release-evidence-01'
    assert not out.exists(), 'Preserve reviews; no implicit retry.'
    prep = json.loads((OUT / 'preparation.json').read_text(encoding='utf-8'))
    state = json.loads((OUT / 'state.json').read_text(encoding='utf-8'))
    assert state['status'] == 'complete' and state['frozen_candidates']
    assert state['preparation_sha256'] == digest(OUT / 'preparation.json')
    assert all(manifest(ROOT / p) == h for p, h in prep['files'].items())
    assert all(digest(ROOT / p) == h for p, h in prep['source_sha256'].items())
    archive_matches(ARCHIVE, ROOT / CHALLENGER)
    archive_matches(ROOT.parent / 'chessity-agent-v1.53.zip', ROOT / SELECTED)
    validation = json.loads((OUT / 'validation.json').read_text(encoding='utf-8'))
    assert validation['status'] == 'complete' and validation['sha256'] == prep['archive_sha256']['v1.42']
    assert validation['init_ms'] < 90000 and validation['legal_calls'] >= 2
    assert all(v == 'blocked' for v in validation['read_only_checks'].values())
    games, feedback, sources = [], [], {}
    can_advance, comparison_points = False, None
    assert state['matches'], 'No completed comparison to review.'
    for index, match in enumerate(state['matches']):
        path = feedback_path(ROOT / match['result_path'])
        assert digest(path) == match['sha256']
        rows, reviewed, hashed = collect(path)
        assert all(g['candidate_path'] == CHALLENGER for g in rows)
        if index == 0:
            assert match['label'] == 'comparison' and len(rows) == 4
            assert all(g['family'] == 'incumbent' and g['opponent_path'] == SELECTED for g in rows)
            comparison_points = sum(g['score'] for g in rows)
            can_advance = (comparison_points >= 2.5 and any(clean_win(g) for g in rows)
                and all(g['termination'] not in ('flag', 'illegal', 'crash', 'init', 'both_failed')
                    and g.get('failed_colour') is None for g in rows))
            assert can_advance == state['favourable_comparison']
        else:
            assert can_advance and index <= 4
            level = (2400, 2600, 2800, 3000)[index - 1]
            assert match['label'] == f'rated-{level}' and all(g['elo'] == level for g in rows)
            can_advance = advance(rows)
        games.extend(rows)
        feedback.extend(reviewed)
        sources.update(hashed)
    for path in (OUT / 'preparation.json', OUT / 'state.json', OUT / 'validation.json', Path(__file__)):
        sources[str(path.relative_to(ROOT))] = digest(path)
    report = dict(status='complete', challenger='v1.42', comparison_opponent='exactv1.53',
        archive_sha256=prep['archive_sha256'], source_sha256=sources, **summarize(games),
        comparison_points=comparison_points, favourable_comparison=state['favourable_comparison'],
        historical_v142_summary=prep['historical_summary'], feedback=feedback,
        reviewed_moves=sum(r['own_moves'] for r in feedback), rewarded=sum(r['rewarded'] for r in feedback),
        penalised=sum(r['penalised'] for r in feedback), pending_stage=state.get('pending_stage'),
        calibrated_elo=None, selected_version=None, automatic_promotion=False,
        scope='Small development comparison; separate historical rated results. Frozen playing weights; reviewed policy checkpoints remain experimental.')
    out.mkdir()
    save(out / 'review.json', report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256', 'feedback')}))


if __name__ == '__main__':
    run()
