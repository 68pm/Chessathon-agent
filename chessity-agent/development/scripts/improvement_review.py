"""Audit a fixed confirmation and apply its declared conservative promotion rule."""

import argparse
import json
import math
from pathlib import Path

from scripts.alien_rating_ladder import save_json, sha256
from scripts.fastchess_matches import FAILURES, score_summary
from scripts.magnus_benchmark import SF, manifest
from scripts.record_fastchess import audit_game
from training.fastchess_data import ROOT


def paired_bound(games, attempt):
    if attempt < 1:
        raise ValueError('Confirmation attempts start at one')
    alpha = 0.05 / (attempt * (attempt + 1))
    values = []
    groups = set()
    for pair in sorted({g['pair'] for g in games}):
        rows = [g for g in games if g['pair'] == pair]
        assert len(rows) == 2 and {g['candidate_white'] for g in rows} == {True, False}
        assert len({g['opening_group'] for g in rows}) == 1
        assert rows[0]['opening_group'] not in groups
        groups.add(rows[0]['opening_group'])
        assert all(g['score'] in (0, .5, 1) for g in rows)
        values.append(sum(g['score'] for g in rows) / 2)
    assert values
    mean = sum(values) / len(values)
    lower = max(0.0, mean - math.sqrt(math.log(1 / alpha) / (2 * len(values))))
    return dict(pairs=len(values), mean=mean, one_sided_alpha=alpha, lower_score_bound=lower,
                method='Bounded colour-pair Hoeffding bound; independent groups and stable conditions assumed.')


def audited(path):
    report = json.loads(path.read_text())
    assert report['status'] == 'complete'
    assert len(report['games']) == len(report['schedule'])
    assert report['config'] == dict(base_ms=120000, increment_ms=500, ply_cap=600, workers=2)
    schedule = {g['id']: g for g in report['schedule']}
    assert len(schedule) == len(report['schedule'])
    assert {g['id'] for g in report['games']} == set(schedule)
    for game in report['games']:
        assert all(game[k] == v for k, v in schedule[game['id']].items())
        audit_game(game, report['config'])
    assert report['files'] == {p: manifest(ROOT / p) for p in report['files']}
    assert report['source_files'] == {p: sha256(ROOT / p) for p in report['source_files']}
    assert report['stockfish_sha256'] == sha256(SF)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--label', required=True)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--attempt', type=int, required=True)
    parser.add_argument('--readonly', type=Path, required=True)
    args = parser.parse_args()
    out = ROOT / 'runs/improvement-loop-20260907' / args.label
    comparison, rated = [audited(out / stage / 'results.json') for stage in ['comparison', 'rated']]
    assert len(comparison['games']) == 24 and len(rated['games']) == 16
    assert {g['candidate_path'] for r in [comparison, rated] for g in r['games']} == {args.candidate}
    assert {g['opponent_path'] for g in comparison['games']} == {'candidates/classical-witty-magnus-v1'}
    assert {g['elo'] for g in rated['games']} == {2400, 2600}
    assert {g['opening_group'] for g in comparison['games']}.isdisjoint(
        {g['opening_group'] for g in rated['games']})
    check = json.loads(args.readonly.read_text())
    archive = (ROOT / args.candidate).with_suffix('.zip')
    assert check['sha256'] == sha256(archive)
    assert all(v == 'blocked' for v in check['read_only_checks'].values())
    bound = paired_bound(comparison['games'], args.attempt)
    reasons = []
    if bound['lower_score_bound'] <= .5:
        reasons.append('Predeclared paired score lower bound did not exceed50%.')
    if any(g['termination'] in FAILURES for r in [comparison, rated] for g in r['games']):
        reasons.append('A runtime failure occurred; it cannot support promotion.')
    report = dict(status='complete', candidate=args.candidate, candidate_sha256=sha256(archive),
                  confirmation_attempt=args.attempt, comparison=score_summary(comparison['games']),
                  rated=score_summary(rated['games']), paired_bound=bound,
                  eligible_for_promotion=not reasons, reasons=reasons, goal_achieved=False,
                  highest_setting_defeated=max((g['elo'] for g in rated['games'] if g['score'] == 1), default=None),
                  source_sha256={stage: sha256(out / stage / 'results.json') for stage in ['comparison', 'rated']},
                  limitation='This fixed40-game confirmation cannot certify consistent2600 wins or a human/site Elo. Audit/retire its rated positions as development data before future fitting. Publication/selected ZIP require an explicit final file audit.')
    save_json(out / 'review.json', report)
    print(json.dumps(report, indent=2), flush=True)


if __name__ == '__main__':
    main()
