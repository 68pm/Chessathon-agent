"""Default future match entry point: review and learn after every saved game."""

import argparse
import json
from pathlib import Path

import chess.engine

from scripts import overnight_game, overnight_matches
from scripts.alien_rating_ladder import sha256
from scripts.overnight_capacity import wait_for_capacity
from training.game_feedback import ROOT, normalise_game, review_batch, write_json
from training.reward_policy import fit


def learn_after_game(row, directory):
    _, identity = normalise_game(row)
    root = Path(directory) / 'postgame-feedback'
    marker = root / 'completed' / (identity['game_key'] + '.json')
    if marker.exists():
        saved = json.loads(marker.read_text(encoding='utf-8'))
        checkpoint = root / saved['training']
        if sha256(checkpoint) != saved['training_sha256']:
            raise ValueError('Completed feedback checkpoint changed')
        return [root / saved['review']]
    review_paths = review_batch([row], root / 'reviews')
    # All earlier games in this match enter replay; game and candidate hashes
    # remain distinct. No weights in the running match are mutated.
    all_reviews = sorted((root / 'reviews/games').glob('*/review.json'))
    initial = ROOT / row['candidate_path'] / 'models/player-policy.npz'
    checkpoint = root / 'checkpoints' / identity['game_key']
    fit(all_reviews, initial, checkpoint)
    training = checkpoint / 'training.json'
    write_json(marker, dict(review=review_paths[0].relative_to(root).as_posix(),
        training=training.relative_to(root).as_posix(), training_sha256=sha256(training)))
    return review_paths


def main():
    original_run = overnight_matches.run_game
    original_local = overnight_game.local
    original_uci = chess.engine.SimpleEngine.popen_uci
    original_wait = overnight_matches.wait_for_memory
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--cycle', required=True)
    parser.add_argument('--stage', required=True)
    options, _ = parser.parse_known_args()
    directory = ROOT / 'runs/improvement-loop-20260907' / options.cycle / (
        options.stage + '-' + Path(options.candidate).name)

    def guarded_local(folder):
        wait_for_capacity(ROOT / 'runs/feedback-match-startup-capacity.json')
        return original_local(folder)

    def guarded_uci(*args, **kwargs):
        wait_for_capacity(ROOT / 'runs/feedback-opponent-startup-capacity.json')
        return original_uci(*args, **kwargs)

    def run_and_learn(job, config, out):
        # Finish an interrupted review before starting any new game. Saved game
        # files remain authoritative, so a review failure never replays a game.
        for path in sorted(out.glob('game-*.json')):
            prior = json.loads(path.read_text(encoding='utf-8'))
            overnight_matches.audit_game(prior, config)
            learn_after_game(prior, out)
        row = original_run(job, config, out)
        overnight_matches.audit_game(row, config)
        learn_after_game(row, out)
        return row

    try:
        # Also covers a completely played match whose final review was interrupted.
        for path in sorted(directory.glob('game-*.json')):
            prior = json.loads(path.read_text(encoding='utf-8'))
            overnight_matches.audit_game(prior,
                dict(base_ms=120000, increment_ms=500, ply_cap=600, workers=1))
            learn_after_game(prior, directory)
        overnight_matches.run_game = run_and_learn
        overnight_game.local = guarded_local
        chess.engine.SimpleEngine.popen_uci = staticmethod(guarded_uci)
        overnight_matches.wait_for_memory = wait_for_capacity
        overnight_matches.main()
    finally:
        overnight_matches.run_game = original_run
        overnight_game.local = original_local
        chess.engine.SimpleEngine.popen_uci = original_uci
        overnight_matches.wait_for_memory = original_wait


if __name__ == '__main__':
    main()
