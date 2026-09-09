"""Audit a rejected evening challenger and preserve reviewed development targets."""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import chess
from scripts.evening_common import ROOT, RUN, digest, manifest, save
from scripts.feedback_matches_windows import feedback_path
from scripts.overnight_archive_challenge import archive_matches
from scripts.overnight_portable_fast_screen import audit_feedback
from training.game_feedback import normalise_game


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def run():
    out = RUN / 'final-status.json'
    assert not out.exists(), 'Preserve an existing audit'
    screen = RUN / 'king-step-buffers-screen-01'
    state, prep = read(screen / 'state.json'), read(screen / 'preparation.json')
    assert state['status'] == 'complete' and not state['passed']
    assert state['decision'] == 'reject_challenger_gate' and state['frozen_candidates']
    assert all(row['status'] == 'complete' for row in state['stages'])
    assert all(manifest(ROOT / path) == hashes for path, hashes in prep['files'].items())
    assert all(digest(ROOT / path) == sha for path, sha in prep['source_sha256'].items())
    selected = read(ROOT.parent / 'chessity-agent-version.json')
    assert selected['version'] == 'v1.56'
    assert digest(ROOT.parent / 'chessity-agent.zip') == selected['sha256'] == prep['selected_sha256']
    assert digest(ROOT.parent / 'chessity-agent-v1.56.zip') == selected['sha256']
    archive_matches(ROOT.parent / 'chessity-agent.zip', ROOT / 'runs/daytime-20260909/move-buffers-01/prototype')
    trial_names = ['repetition-02', 'pawn-threat-01', 'king-pressure-01',
                   'queen-pawns-01', 'deep-exchange-01', 'king-step-buffers-01',
                   'king-step-buffers-quality-01', 'tapered-value-01']
    trials = []
    for name in trial_names:
        data = read(RUN / name / 'state.json')
        assert data['status'] == 'complete'
        trials.append(dict(name=name, sha256=digest(RUN / name / 'state.json'),
            **{key: data[key] for key in ('passed', 'decision', 'aggregate_cpu_speedup',
                'median_cpu_speedup', 'clock_mean_depth', 'mean_regret_cp',
                'regressions', 'broad_before', 'broad_after', 'model_sha256') if key in data}))
    colour = read(RUN / 'tapered-value-01/exposed-development.json')
    assert not colour['passed']
    save(RUN / 'tapered-value-01/public-colour-summary.json',
         {key: colour[key] for key in ('status', 'passed', 'cohorts', 'model_sha256')})
    games, reviews, corrections, sources = [], [], [], {}
    pack = RUN / 'completed-games'
    pack.mkdir()
    for item in state['matches']:
        path = ROOT / item['result_path']
        assert digest(path) == item['sha256']
        result = audit_feedback(path)
        assert result['status'] == 'complete' and result['config']['base_ms'] == 120000
        assert result['config']['increment_ms'] == 500
        sources[str(path.relative_to(ROOT))] = digest(path)
        feedback = feedback_path(path.parent / 'postgame-feedback')
        for game in result['games']:
            assert game['termination'] == 'checkmate' and game['failed_colour'] is None
            _, identity = normalise_game(game)
            marker = read(feedback / 'completed' / (identity['game_key'] + '.json'))
            review_path = feedback / marker['review']
            review = read(review_path)
            assert review['status'] == 'complete'
            name = f"{item['label']}-game-{game['id']}"
            (pack / (name + '.pgn')).write_text(game['pgn'] + '\n', encoding='utf-8')
            summary = dict(name=name, white=game['candidate_white'], score=game['score'],
                termination=game['termination'], game_key=identity['game_key'],
                own_moves=review['own_moves'], rewarded=review['rewarded'],
                penalised=review['penalised'], labels=review['labels'],
                review_sha256=digest(review_path), training_sha256=marker['training_sha256'])
            negative = [row for row in review['rows'] if row['reward'] is not None and row['reward'] < 0]
            summary['correction_phases'] = dict(Counter(
                'endgame' if 'endgame' in row['tags'] else 'opening' if 'opening' in row['tags'] else 'middlegame'
                for row in negative))
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
                corrections.append(dict(game=name, game_key=identity['game_key'], source_sha256=digest(review_path),
                    target_san=board.san(chess.Move.from_uci(target)) if target else None, **row))
            reviews.append(summary)
            games.append(game)
    assert len(games) == 4 and sum(game['score'] for game in games) < 3
    targets = dict(status='complete', rows=corrections, split='development',
        scope='Reviewed root actions, including uncertain alternatives. Null policy targets must remain null. '
              'No independently labelled descendant values are supplied. These games are now exposed development data; '
              'do not reuse their replay as independent evidence for a trained successor.')
    save(RUN / 'development-targets.json', targets)
    phases = Counter()
    for row in reviews:
        phases.update(row['correction_phases'])
    final = dict(status='complete', completed_utc=datetime.now(timezone.utc).isoformat(),
        selected_version='v1.56', selected_sha256=selected['sha256'], new_release_created=False,
        site_submission=False, site_active_version='unverified', calibrated_elo=None,
        challenger=dict(name='king-step-buffers-01', wins=sum(g['score'] == 1 for g in games),
            draws=sum(g['score'] == .5 for g in games), losses=sum(g['score'] == 0 for g in games),
            required_points=3, actual_points=sum(g['score'] for g in games), opponent='exact selected v1.56',
            qualification=False, operational_failures=0),
        trials=trials, reviewed_games=reviews, reviewed_moves=sum(r['own_moves'] for r in reviews),
        positive_labels=sum(r['rewarded'] for r in reviews), negative_labels=len(corrections),
        correction_phases=dict(phases), usable_corrections=sum(r['policy_target'] is not None for r in corrections),
        sources=sources, colour_value_check=colour['cohorts'],
        target_sha256=digest(RUN / 'development-targets.json'),
        rated_games_this_run=0, scope='Small development screen. No calibrated Elo or universal strength proof. '
        'No candidate met every promotion gate. Frozen playing weights exclude experimental postgame fits.')
    save(out, final)
    c = final['challenger']
    report = f"""# Chessity improvement results — 9 September, evening

**Keep v1.56.** The only challenger that reached match testing scored **{c['wins']} wins, {c['draws']} draws, {c['losses']} losses against exact v1.56** at120 seconds +0.5 seconds. It needed3/4 points. No v1.57 was created, no upload alias changed, and no new competition submission was made.

The four games used two preset openings, B12 Caro-Kann Advance Short and D48 Meran, with both colours. All ended by checkmate with no operational failures. The challenger was already ineligible after its third game; the fourth had started and was completed and reviewed. The2400/2600 stages were skipped after rejection. These results do not establish an Elo rating.

| Change tested | Measured result | Decision |
|---|---|---|
| Faster repetition query | Exact fixed-work parity; aggregate CPU speed ratio1.001, median0.988 | Reject: insufficient speed gain |
| Protect quiet pawn threats from reductions | More tactical regret and a new major error | Reject |
| Coordinated king-pressure evaluation | Fixed one example but caused other major errors | Reject |
| Queen-aware passed-pawn correction | About2% mean-regret improvement; below the declared10% gate | Reject |
| Exchange-aware ordering deeper in search | No mean-regret improvement | Reject |
| Tapered learned position evaluator | Broad development error improved8.5%, but separate White and Black checks worsened | Reject |
| King-step legal check combined with v1.56 buffers | About25% faster in aggregate fixed-work CPU tests; identical fixed-work decisions and unchanged tactical regret; failed actual games | Reject for release |

The learned evaluator was an original768-weight, symmetric middlegame/endgame position head fitted to13,386 existing labelled rows. It improved the broad development fit, but White mean absolute error rose95.6→115.4cp and Black43.5→68.4cp. It was never integrated into the playing agent. The three reserved Italian games remain unused. The first repetition preparation also had a setup/test failure; that failed attempt remains archived separately.

Every completed game went through Stockfish review: **{final['reviewed_moves']} challenger moves**, **{final['positive_labels']} positive labels** and **{final['negative_labels']} negative labels**. Experimental reward-policy outputs remain separate from the frozen playing agent. The correction pack contains **{final['usable_corrections']} legal, independently supported alternative moves**; disagreements keep a null target. Root rewards are not substituted for searched-position value labels.

Corrections by phase: {dict(phases)}. These are thresholded corrections, not a rating or an estimate of how often all moves are wrong.

The Caro-Kann Black loss exposed premature pawn pushes (9...b5 instead of...g6), a queen excursion (21...Qa3 instead of...Be7), and missed late defences. Raw learned policy preferences already favoured the verified alternative in three of four inspected major-error positions. That comparison does not measure full search activation or prove causality; it argues against assuming the policy alone is responsible.

In the Meran White loss,30.Rb6 allowed...Rd1 and lost a near-equal opportunity. At80k/320k requested Stockfish budgets,30.Rb8 evaluated0/−6cp, versus−350/−404cp for Rb6. The18.Be5 error had218/230cp regret but different teacher-best alternatives at the two budgets, so no single correction move was assigned. These cases support testing quiet defensive alternatives and rook activity before more broad opening data.

Next work should preserve the speed experiment but improve the decisions it exposes: inspect bounded defensive continuations from these failures, independently label their suitable descendant positions, and check a future evaluator on fresh games. Training on these four games makes their later replays development checks. Any successor still needs a short comparison against exact v1.56 before a release number, plus the declared rated gates.

The selected v1.56's earlier screen remains:2W/0D/0L versus v1.55,2W/0D/0L versus v1.53,0W/1D/1L at nominal2400 and0W/1D/1L at nominal2600. Those nominal settings are not measured Elo. Today's head-to-head result adds evidence for retaining v1.56, without proving it universally strongest.

Selected ZIP SHA256: `{selected['sha256']}`. Runtime remains read-only. Browser control was unavailable; the currently active competition submission was not verified. GitHub publication is recorded separately after push verification.
"""
    for path in (ROOT / 'docs/EVENING_RESULTS_20260909.md', ROOT.parent / 'chessity-evening-improvement-20260909.md'):
        assert not path.exists()
        path.write_text(report, encoding='utf-8')
    print(json.dumps({key: final[key] for key in ('selected_version', 'challenger', 'reviewed_moves', 'positive_labels', 'negative_labels', 'usable_corrections', 'correction_phases')}), flush=True)


if __name__ == '__main__':
    run()
