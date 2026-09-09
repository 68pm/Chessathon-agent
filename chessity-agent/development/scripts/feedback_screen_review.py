"""Audit completed small screens for reporting; never promote or modify a runtime."""

import argparse
import json
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

from scripts.feedback_matches_windows import feedback_path
from scripts.feedback_position_plan import choose_roots, validate_review
from scripts.overnight_geometry_trial import ROOT, digest, manifest, save
from scripts.overnight_portable_screen import (
    FAILURES,
    advance,
    audit_feedback,
    clean_win,
    comparison_passes,
)
from training.game_feedback import normalise_game


def summarize(games):
    if not games:
        return dict(groups={}, highest_clean_nominal_win=None)
    assert len({g['candidate_path'] for g in games}) == 1, 'Keep candidate versions separate.'
    groups = defaultdict(list)
    highest = None
    for game in games:
        assert type(game['candidate_white']) is bool and game['score'] in (0., .5, 1.)
        family = game['family']
        if family.startswith('stockfish:'):
            level = int(family.split(':')[1])
            assert game['elo'] == level, 'Opponent display label and setting disagree.'
            if clean_win(game):
                highest = max(highest or 0, level)
        else:
            assert family == 'incumbent'
        groups[family].append(game)

    def counts(items):
        return dict(games=len(items), wins=sum(g['score'] == 1 for g in items),
            draws=sum(g['score'] == .5 for g in items), losses=sum(g['score'] == 0 for g in items),
            clean_wins=sum(clean_win(g) for g in items),
            operational_games=sum(g['termination'] in FAILURES or g.get('failed_colour') is not None for g in items))

    return dict(groups={family: dict(**counts(items),
        by_colour={name: counts([g for g in items if g['candidate_white'] == colour])
            for name, colour in (('white', True), ('black', False))},
        terminations=dict(Counter(g['termination'] for g in items))) for family, items in groups.items()},
        highest_clean_nominal_win=highest)


def validate_ascent(matches):
    assert matches and matches[0]['label'] == 'comparison'
    comparison = matches[0]['games']
    assert len(comparison) == 4 and {g['family'] for g in comparison} == {'incumbent'}
    accepted = comparison_passes(comparison)
    expected = (2400, 2600, 2800, 3000)
    for index, match in enumerate(matches[1:]):
        assert accepted, 'Rated ascent occurred without a qualifying previous stage.'
        assert index < len(expected) and match['label'] == f'rated-{expected[index]}'
        assert {g['family'] for g in match['games']} == {f'stockfish:{expected[index]}'}
        accepted = advance(match['games'])
    return dict(comparison_passed=comparison_passes(comparison),
        comparison_points=sum(g['score'] for g in comparison),
        comparison_signal='favourable_small_sample' if sum(g['score'] for g in comparison) > 2 else
            'tied_small_sample' if sum(g['score'] for g in comparison) == 2 else 'unfavourable_small_sample',
        final_pair_qualifies_for_next=accepted if len(matches) > 1 else None)


def review(directory):
    directory = directory.resolve()
    assert directory.is_relative_to(ROOT / 'runs/overnight-20260909')
    out = directory / 'release-evidence-01'
    assert not out.exists(), 'Preserve existing reviews; use a separately declared attempt.'
    screen_path = directory / 'candidate-screen-01/state.json'
    screen = json.loads(screen_path.read_text(encoding='utf-8'))
    assert screen['status'] == 'complete' and screen['frozen_candidates'], 'Wait for the full screen; a failed or partial screen needs explicit review.'
    prep_path = directory / 'preparation.json'
    prep = json.loads(prep_path.read_text(encoding='utf-8'))
    assert all(manifest(ROOT / p) == prep['candidate_files'][label] for label, p in prep['candidates'].items())
    assert digest(directory / 'state.json') == screen['trial_sha256']
    assert all(digest(ROOT / p) == value for p, value in screen['source_files'].items())
    validation_path = directory / 'candidate-screen-01/validation.json'
    validation = json.loads(validation_path.read_text(encoding='utf-8'))
    archive = directory / 'prototype.zip'
    assert validation['status'] == 'complete' and validation['sha256'] == screen['package_sha256'] == digest(archive)
    assert validation['init_ms'] < 90000 and validation['legal_calls'] >= 2
    assert all(value == 'blocked' for value in validation['read_only_checks'].values())
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        assert len(zipped.namelist()) == len(set(zipped.namelist()))
        assert sum(i.file_size for i in zipped.infolist()) < 50_000_000
        for name in zipped.namelist():
            path = Path(name)
            assert not path.is_absolute() and '..' not in path.parts
            assert zipped.read(name) == (ROOT / prep['candidates']['prototype'] / path).read_bytes()
    matches, games, feedback, sources = [], [], [], {}
    for match in screen['matches']:
        path = feedback_path(ROOT / match['result_path'])
        assert digest(path) == match['sha256']
        result = audit_feedback(path)
        assert result['config']['base_ms'] == 120000 and result['config']['increment_ms'] == 500
        assert all((ROOT / g['candidate_path']).resolve() == (ROOT / prep['candidates']['prototype']).resolve() for g in result['games'])
        matches.append(dict(label=match['label'], games=result['games']))
        games.extend(result['games'])
        sources[str(path.relative_to(feedback_path(ROOT)))] = digest(path)
        for game in result['games']:
            _, identity = normalise_game(game)
            root = path.parent / 'postgame-feedback'
            marker = json.loads((root / 'completed' / (identity['game_key'] + '.json')).read_text(encoding='utf-8'))
            review_path, training_path = root / marker['review'], root / marker['training']
            doc = json.loads(review_path.read_text(encoding='utf-8'))
            training = json.loads(training_path.read_text(encoding='utf-8'))
            validate_review(doc)
            assert doc['identity']['game'] == identity and training['status'] == 'complete'
            sources[str(review_path.relative_to(feedback_path(ROOT)))] = digest(review_path)
            sources[str(training_path.relative_to(feedback_path(ROOT)))] = digest(training_path)
            selected = [dict(ply=row['ply'], fullmove=row['fullmove'], played=row['san'],
                target_uci=row['policy_target'], phase=row['tags'][0], reason=reason,
                regret_cp=row['regret_cp'], root_reward=row['reward']) for row, reason in choose_roots(doc['rows'])]
            feedback.append(dict(stage=match['label'], id=game['id'], game_key=identity['game_key'],
                candidate_white=game['candidate_white'], score=game['score'], own_moves=doc['own_moves'],
                rewarded=doc['rewarded'], penalised=doc['penalised'], labels=doc['labels'],
                phases=dict(Counter(r['tags'][0] for r in doc['rows'])),
                experimental_policy_examples=training['examples'], experimental_policy_updates=training['updates'],
                selected_diagnostic_roots=selected))
    ascent = validate_ascent(matches)
    assert ascent['comparison_passed'] == screen['provisional_comparison_passed']
    for path in (screen_path, prep_path, validation_path, Path(__file__),
                 ROOT / 'scripts/feedback_position_plan.py', ROOT / 'scripts/overnight_portable_screen.py',
                 ROOT / 'tests/test_feedback_screen_review.py', ROOT / 'docs/OVERNIGHT_FEEDBACK_SCREEN_REVIEW_20260909.md'):
        sources[str(path.relative_to(ROOT))] = digest(path)
    report = dict(status='complete', candidate=prep['candidates']['prototype'],
        control=prep['candidates']['baseline'], package_sha256=digest(archive),
        source_sha256=sources, **summarize(games), **ascent, feedback=feedback,
        total_reviewed_moves=sum(g['own_moves'] for g in feedback),
        rewarded=sum(g['rewarded'] for g in feedback), penalised=sum(g['penalised'] for g in feedback),
        calibrated_elo=None, selected_version=None, automatic_promotion=False,
        limitation='Small development screen versus compiler-repaired53, not exact selected53 ZIP. Nominal Stockfish settings are not calibrated site/human Elo. Every operational result remains in W/D/L; only clean played wins determine highest beaten setting. Review all evidence before selecting a release.')
    out.mkdir()
    save(out / 'review.json', report)
    print(json.dumps({k:v for k,v in report.items() if k not in ('source_sha256', 'feedback')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    review(parser.parse_args().run)
