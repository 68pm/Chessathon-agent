"""Derive and review the selected agent's other side of completed comparison games."""

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.feedback_matches_windows import feedback_path
from scripts.overnight_archive_challenge import CHALLENGER, DEADLINE, SELECTED
from scripts.overnight_archive_challenge import OUT as CHALLENGE
from scripts.overnight_geometry_trial import ROOT, check_stop, digest, manifest, save
from scripts.overnight_portable_fast_screen import audit_feedback
from scripts.record_fastchess import audit_game
from training.game_feedback import normalise_game

OUT = ROOT / 'runs/overnight-20260909/archive-opponent-feedback-01'
SOURCE = ROOT / 'runs/improvement-loop-20260907/n9-archive-42-comparison/comparison-compiled-reductions-v1/results.json'


def opposite(record):
    assert record['family'] == 'incumbent' and type(record['candidate_white']) is bool
    derived = dict(record, candidate_path=record['opponent_path'], opponent_path=record['candidate_path'],
        candidate_white=not record['candidate_white'], score=1. - record['score'])
    normalise_game(derived)
    return derived


def prepare():
    assert not OUT.exists(), 'Preserve prior preparations.'
    original = audit_feedback(SOURCE)
    assert len(original['games']) == 4
    prepared = json.loads((CHALLENGE / 'preparation.json').read_text(encoding='utf-8'))
    assert all(manifest(ROOT / p) == h for p, h in prepared['files'].items())
    games = []
    for record in original['games']:
        assert record['candidate_path'] == CHALLENGER and record['opponent_path'] == SELECTED
        derived = opposite(record)
        derived.update(source_result_sha256=digest(SOURCE),
            source_game_id=f"archive-comparison-game-{record['id']}-selected-perspective",
            candidate_version='v1.53:' + prepared['archive_sha256']['v1.53'])
        audit_game(derived, original['config'])
        assert derived['pgn'] == record['pgn'] and derived['moves'] == record['moves']
        assert derived['failed_colour'] == record['failed_colour']
        games.append(derived)
    paths = [Path(__file__), ROOT / 'docs/OVERNIGHT_OPPONENT_FEEDBACK_20260909.md', SOURCE,
        CHALLENGE / 'preparation.json', ROOT / 'scripts/feedback_batch.py',
        ROOT / 'training/game_feedback.py', ROOT / 'training/reward_policy.py',
        ROOT / SELECTED / 'models/player-policy.npz']
    OUT.mkdir()
    save(OUT / 'games.json', dict(status='complete', games=games, source_sha256=digest(SOURCE),
        scope='Same played games, selected-v1.53 perspective. Not extra strength games.'))
    save(OUT / 'preparation.json', dict(source_sha256={str(p.relative_to(ROOT)):digest(p) for p in paths},
        games_sha256=digest(OUT / 'games.json'), frozen_players=prepared['files'], budget_seconds=900,
        scope='Only postgame feedback; no new game, runtime fit, release selection or Elo.'))


def verify(prep):
    assert all(digest(ROOT / p) == h for p, h in prep['source_sha256'].items())
    assert digest(OUT / 'games.json') == prep['games_sha256']
    assert all(manifest(ROOT / p) == h for p, h in prep['frozen_players'].items())


def worker():
    from scripts import feedback_batch
    from training import game_feedback, reward_policy

    prep = json.loads((OUT / 'preparation.json').read_text(encoding='utf-8'))
    verify(prep)
    old_stop = game_feedback.stop_check

    def stop():
        old_stop()
        check_stop()

    game_feedback.stop_check = reward_policy.stop_check = stop
    sys.argv = [__file__, '--source', str(feedback_path(OUT / 'games.json')),
        '--out', str(feedback_path(OUT / 'feedback')),
        '--initial-policy', str(feedback_path(ROOT / SELECTED / 'models/player-policy.npz'))]
    feedback_batch.main()
    verify(prep)


def run():
    from scripts.overnight_capacity import wait_for_capacity

    prep = json.loads((OUT / 'preparation.json').read_text(encoding='utf-8'))
    assert not (OUT / 'state.json').exists()
    assert json.loads((CHALLENGE / 'state.json').read_text(encoding='utf-8'))['status'] == 'complete'
    check_stop()
    verify(prep)
    assert (DEADLINE - datetime.now(timezone.utc)).total_seconds() >= 900, 'Leave prepared; insufficient time.'
    wait_for_capacity(OUT / 'capacity.json', minimum_memory_mb=1400, wait_seconds=120)
    state = dict(status='running', preparation_sha256=digest(OUT / 'preparation.json'))
    save(OUT / 'state.json', state)
    started = time.monotonic()
    with (OUT / 'feedback.log').open('w', encoding='utf-8') as log:
        process = subprocess.Popen([sys.executable, '-X', 'utf8', '-m',
            'scripts.overnight_opponent_feedback', '--worker'], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        state['pid'] = process.pid
        save(OUT / 'state.json', state)
        try:
            while process.poll() is None:
                check_stop()
                if time.monotonic() - started > 900:
                    raise TimeoutError('Bounded opponent review exhausted its900seconds')
                time.sleep(.5)
            assert process.returncode == 0, 'Opponent review failed; retain partial evidence.'
            verify(prep)
            state.update(status='complete', experimental_policy_only=True, selected_changed=False)
        except BaseException as error:
            state.update(status='failed', error=repr(error))
            if process.poll() is None:
                if os.name == 'nt':
                    subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], capture_output=True,
                        check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    process.kill()
                process.wait(timeout=15)
            raise
        finally:
            state['elapsed_seconds'] = time.monotonic() - started
            save(OUT / 'state.json', state)
            print(json.dumps(state), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    prepare() if args.prepare else worker() if args.worker else run()
