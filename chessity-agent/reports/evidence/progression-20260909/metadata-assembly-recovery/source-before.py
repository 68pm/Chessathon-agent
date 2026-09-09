"""Archive completed progression games and verified correction targets, without promotion."""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import chess

from scripts.progression_common import ROOT, RUN, BASE, digest, manifest, save
from scripts.feedback_matches_windows import feedback_path
from scripts.overnight_archive_challenge import archive_matches
from scripts.overnight_portable_fast_screen import audit_feedback
from scripts.progression_release_audit import summarise
from scripts.progression_screen import all_required_pass
from training.game_feedback import normalise_game


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def archive(screen_name='root-verification-01-screen-01'):
    output = RUN / 'session-audit.json'
    assert not output.exists(), 'Preserve consumed evidence archives'
    screen = RUN / screen_name
    state, prep = read(screen / 'state.json'), read(screen / 'preparation.json')
    assert state['status'] == 'complete' and state['frozen_candidates']
    assert all(row['status'] == 'complete' for row in state['stages'])
    assert all(manifest(ROOT / p) == h for p, h in prep['files'].items())
    assert all(digest(ROOT / p) == h for p, h in prep['source_sha256'].items())
    assert digest(ROOT.parent / 'chessity-agent.zip') == prep['selected_sha256']
    archive_matches(ROOT.parent / 'chessity-agent.zip', BASE)
    development = RUN / 'v156-development2400-01/state.json'
    dev = read(development)
    assert dev['status'] == 'complete'
    paths = [dict(label='v156-development2400', candidate='exact selected v1.56',
        result_path='runs/improvement-loop-20260907/p9-v156-development2400-01/rated-prototype/results.json')]
    paths.extend(dict(item, candidate='root-verification-01') for item in state['matches'])
    games, reviews, corrections, sources = {}, [], [], {}
    directory = RUN / 'completed-games'
    assert not directory.exists()
    directory.mkdir()
    for item in paths:
        path = ROOT / item['result_path']
        if 'sha256' in item:
            assert digest(path) == item['sha256']
        result = audit_feedback(path)
        assert result['config']['base_ms'] == 120000 and result['config']['increment_ms'] == 500
        sources[str(path.relative_to(ROOT))] = digest(path)
        games[item['label']] = result['games']
        feedback = feedback_path(path.parent / 'postgame-feedback')
        for game in result['games']:
            _, identity = normalise_game(game)
            marker = read(feedback / 'completed' / (identity['game_key'] + '.json'))
            review_path = feedback / marker['review']
            review = read(review_path)
            assert review['status'] == 'complete'
            name = f"{item['label']}-game-{game['id']}"
            (directory / (name + '.pgn')).write_text(game['pgn'] + '\n', encoding='utf-8')
            negative = [r for r in review['rows'] if r['reward'] is not None and r['reward'] < 0]
            summary = dict(name=name, candidate=item['candidate'], white=game['candidate_white'],
                score=game['score'], termination=game['termination'], game_key=identity['game_key'],
                own_moves=review['own_moves'], rewarded=review['rewarded'], penalised=review['penalised'],
                review_sha256=digest(review_path), training_sha256=marker['training_sha256'],
                correction_phases=dict(Counter('endgame' if 'endgame' in r['tags'] else
                    'opening' if 'opening' in r['tags'] else 'middlegame' for r in negative)))
            for row in negative:
                board = chess.Board(row['start_fen'])
                for uci in row['history']:
                    move = chess.Move.from_uci(uci)
                    assert move in board.legal_moves
                    board.push(move)
                assert board.fen() == row['fen'] and board.turn == row['white']
                assert chess.Move.from_uci(row['played']) in board.legal_moves
                target = row['policy_target']
                assert target is None or chess.Move.from_uci(target) in board.legal_moves
                assert row['static_value_target'] is None
                corrections.append(dict(game=name, candidate=item['candidate'], game_key=identity['game_key'],
                    source_sha256=digest(review_path), played_san=board.san(chess.Move.from_uci(row['played'])),
                    target_san=board.san(chess.Move.from_uci(target)) if target else None, **row))
            reviews.append(summary)
    assert all_required_pass(games) == state['passed']
    trials = []
    for name in ('root-pvs-01', 'pv-guard-01', 'safe-mobility-01', 'context-value-01',
                 'reward-policy-01', 'reviewed-policy-01', 'root-verification-01'):
        path = RUN / name / 'state.json'; data = read(path)
        assert data['status'] == 'complete'
        trials.append(dict(name=name, sha256=digest(path), **{k: data[k] for k in
            ('passed', 'decision', 'mean_regret_cp', 'regressions', 'model_sha256', 'colours',
             'broad_mse_before', 'broad_mse_after', 'target_metrics', 'objective_before',
             'objective_after', 'good', 'corrections', 'broad_replay') if k in data}))
    targets = dict(status='complete', rows=corrections, split='development',
        scope='Reviewed root actions. Null alternatives and mate uncertainty remain intact. '
              'These games are exposed development data for future training; root rewards are not leaf value labels.')
    save(RUN / 'development-targets.json', targets)
    field = RUN / 'field-01'
    field_state = read(field / 'state.json')
    assert field_state['status'] == 'complete'
    public_reviews, public_targets = [], []
    for item in field_state['new_games']:
        record, label = item['record'], item['label']
        _, identity = normalise_game(record)
        feedback = feedback_path(field / (label + '-review'))
        review_path = feedback / 'games' / identity['game_key'] / 'review.json'
        review = read(review_path)
        assert review['status'] == 'complete'
        training = read(feedback / 'reward-policy/training.json')
        assert training['status'] == 'complete' and not training['promoted']
        assert digest(feedback / 'reward-policy/player-policy.npz') == training['model_sha256']
        negative = [r for r in review['rows'] if r['reward'] is not None and r['reward'] < 0]
        public_reviews.append(dict(label=label, round=record['id'], url=item['url'],
            opponent=record['opponent'], score=record['score'], white=record['candidate_white'],
            version=record['candidate_version'], game_key=identity['game_key'],
            own_moves=review['own_moves'], rewarded=review['rewarded'], penalised=review['penalised'],
            review_sha256=digest(review_path), model_sha256=training['model_sha256'],
            correction_phases=dict(Counter('endgame' if 'endgame' in r['tags'] else
                'opening' if 'opening' in r['tags'] else 'middlegame' for r in negative))))
        for row in negative:
            board = chess.Board(row['start_fen'])
            for uci in row['history']:
                move = chess.Move.from_uci(uci)
                assert move in board.legal_moves
                board.push(move)
            assert board.fen() == row['fen'] and board.turn == row['white']
            target = row['policy_target']
            assert target is None or chess.Move.from_uci(target) in board.legal_moves
            assert row['static_value_target'] is None
            public_targets.append(dict(label=label, round=record['id'], url=item['url'],
                game_key=identity['game_key'], version=record['candidate_version'],
                source_sha256=digest(review_path),
                target_san=board.san(chess.Move.from_uci(target)) if target else None, **row))
    assert len(public_reviews) == 6
    save(RUN / 'public-targets.json', dict(status='complete', split='development', rows=public_targets,
        scope='Public completed-game root actions; submission hashes unverified. Independent descendant labels '
              'remain necessary for position-value fitting. These reviews trained separate experimental policies.'))
    phases = Counter()
    for row in reviews:
        phases.update(row['correction_phases'])
    groups = {label: summarise(rows) for label, rows in games.items()}
    groups['challenger-versus56'] = summarise([g for label, rows in games.items()
        if label.startswith('versus56-') for g in rows])
    final = dict(status='complete', completed_utc=datetime.now(timezone.utc).isoformat(),
        incumbent='v1.56', incumbent_sha256=prep['selected_sha256'],
        challenger_qualified=state['passed'], decision=state['decision'],
        new_release_created_by_this_audit=False, site_submission=False, calibrated_elo=None,
        trials=trials, groups=groups, reviewed_games=reviews,
        reviewed_moves=sum(r['own_moves'] for r in reviews),
        positive_labels=sum(r['rewarded'] for r in reviews), negative_labels=len(corrections),
        usable_corrections=sum(r['policy_target'] is not None for r in corrections),
        correction_phases=dict(phases), sources=sources,
        public_reviews=public_reviews, public_source_sha256=digest(field / 'state.json'),
        public_targets_sha256=digest(RUN / 'public-targets.json'),
        targets_sha256=digest(RUN / 'development-targets.json'),
        scope='Short practical gates, no universal strength proof or calibrated Elo. '
              'All playing manifests stayed frozen; postgame policy fits remain experimental.')
    save(output, final)
    print(json.dumps({k: final[k] for k in ('challenger_qualified', 'groups', 'reviewed_moves',
        'positive_labels', 'negative_labels', 'usable_corrections', 'correction_phases')}), flush=True)


if __name__ == '__main__':
    archive()
