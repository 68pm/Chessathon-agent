"""Summarise a small, frozen multi-version diagnostic without automatic promotion."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.alien_rating_ladder import save_json, sha256
from scripts.fastchess_matches import FAILURES
from scripts.improvement_review import audited
from scripts.magnus_benchmark import manifest
from training.fastchess_data import ROOT


def review(plan_path):
    plan = json.loads(plan_path.read_text(encoding='utf-8'))
    spec = plan['review']
    out = ROOT / plan['output']
    archive = ROOT / spec['candidate_zip']
    readonly = json.loads((ROOT / spec['readonly']).read_text(encoding='utf-8'))
    assert readonly['sha256'] == spec['candidate_sha256'] == sha256(archive)
    assert all(v == 'blocked' for v in readonly['read_only_checks'].values())
    assert readonly['legal_calls'] == 2 and readonly['clock_ms'] == 120000
    assert spec['files'] == {p: manifest(ROOT / p) for p in spec['files']}
    assert spec['source_files'] == {p: sha256(ROOT / p) for p in spec['source_files']}
    groups, games, queue = {}, [], []
    pool_sha = sha256(ROOT / spec['pool'])
    for dataset in spec['datasets']:
        matches_path = ROOT / dataset['matches']
        source = audited(matches_path)
        assert source['opponent_pool_sha256'] == pool_sha
        phase_path = ROOT / dataset['phase']
        phase = json.loads(phase_path.read_text(encoding='utf-8'))
        assert phase['status'] == 'complete' and phase['matches_sha256'] == sha256(matches_path)
        assert len(source['games']) == 2 * len(dataset['opponents'])
        assert set(phase['groups']) == {o['family'] for o in dataset['opponents']}
        for opponent in dataset['opponents']:
            rows = [g for g in source['games'] if g['family'] == opponent['family']]
            assert len(rows) == 2 and {g['candidate_white'] for g in rows} == {True, False}
            assert all(g['candidate_path'] == spec['candidate'] for g in rows)
            assert all(g['opening'] == spec['opening_moves'] for g in rows)
            if 'path' in opponent:
                assert all(g['opponent_path'] == opponent['path'] for g in rows)
            else:
                assert all(g['elo'] == opponent['elo'] for g in rows)
            label = opponent['label']
            assert label not in groups
            groups[label] = dict(
                games=2, wins=sum(g['score'] == 1 for g in rows),
                draws=sum(g['score'] == .5 for g in rows), losses=sum(g['score'] == 0 for g in rows),
                score=sum(g['score'] for g in rows) / 2,
                candidate_failures=sum(g.get('failed_colour') == ('white' if g['candidate_white'] else 'black') for g in rows),
                runtime_failures=sum(g['termination'] in FAILURES for g in rows),
                phase=phase['groups'][opponent['family']],
                results_sha256=sha256(matches_path), phase_sha256=sha256(phase_path))
            for game in rows:
                diagnosis = next(g for g in phase['games'] if g['id'] == game['id'])
                games.append(dict(opponent_label=label, **diagnosis))
                (out / f"{label}-game-{game['id']:03}.pgn").write_text(game['pgn'] + '\n', encoding='utf-8', newline='\n')
            for target in phase['review_queue']:
                if target['opponent'] == opponent['family']:
                    queue.append(dict(opponent_label=label, **target))
    assert len(groups) == 5 and len(games) == spec['expected_games'] == 10
    result = dict(status='complete', completed_utc=datetime.now(timezone.utc).isoformat(),
        candidate=spec['candidate'], candidate_sha256=spec['candidate_sha256'],
        selected_before_review=spec['selected_before_review'], selected_changed=False,
        time_control='120+0.5', games=games, groups=groups, review_queue=queue,
        highest_nominal_setting_defeated=max((level for level in [2400, 2600]
            if groups[f'stockfish-{level}']['wins'] > 0), default=None),
        new_teacher_nodes=0, plan_sha256=sha256(plan_path), source_code_sha256=sha256(__file__),
        scope='Ten predeclared diagnostic games, one common opening with colours reversed. '
              'All outcomes retained. Phase warnings guide the next change; they are not proof of causation. '
              'Stockfish handicap settings are not a calibrated agent Elo. No automatic promotion or pool retirement.')
    save_json(out / 'review.json', result)
    print(json.dumps(dict(status='complete', games=len(games),
        groups={k: {field: v[field] for field in ['wins', 'draws', 'losses', 'candidate_failures']}
                for k, v in groups.items()}, queued=len(queue),
        highest_nominal_setting_defeated=result['highest_nominal_setting_defeated'])), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan', type=Path, required=True)
    review(parser.parse_args().plan)
