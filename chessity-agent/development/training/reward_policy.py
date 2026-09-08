"""Bounded teacher-reward policy fitting; never updates the selected playing package."""

import os

for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'

import argparse
import json
from pathlib import Path

import chess
import numpy as np

from engine.player_policy import SIZE, encode_moves
from nn.model import Network
from nn.optim import Adam
from scripts.alien_rating_ladder import sha256
from scripts.overnight_capacity import wait_for_capacity
from training.game_feedback import ROOT, digest, stop_check, write_json


def probabilities(logits):
    scaled = logits - logits.max()
    output = np.exp(scaled)
    return output / output.sum()


def reward_loss(logits, target, weight, anchor, anchor_weight=2.):
    """Positive moves are reinforced; bad moves prefer the verified correction."""
    probs = probabilities(np.asarray(logits))
    if not 0 <= target < len(probs) or not 0 <= weight <= 1:
        raise ValueError('Invalid reward target')
    anchor = np.asarray(anchor)
    if len(anchor) != len(probs) or np.any(anchor < 0) or not np.isclose(anchor.sum(), 1):
        raise ValueError('Invalid reference policy')
    loss = -weight * np.log(max(probs[target], 1e-30))
    loss += anchor_weight * np.sum(anchor * (np.log(np.maximum(anchor, 1e-30))
                                              - np.log(np.maximum(probs, 1e-30))))
    gradient = weight * probs.copy() + anchor_weight * (probs - anchor)
    gradient[target] -= weight
    return float(loss), gradient


def read_examples(paths):
    groups, seen = [], set()
    for path in paths:
        review = json.loads(Path(path).read_text(encoding='utf-8'))
        if review['status'] != 'complete':
            raise ValueError('Never train on incomplete reviews')
        group = []
        for row in review['rows']:
            if row['policy_target'] is None or not row['policy_weight']:
                continue
            key = digest(dict(fen=row['fen'], history=row['history'], target=row['policy_target']))
            if key in seen:
                continue
            seen.add(key)
            group.append(dict(row, group=review['identity']['game']['game_key']))
        if group:
            groups.append(group)
    # A long easy win cannot overwhelm a short loss. Take up to 48 per game,
    # keeping both reward signs when present, without endlessly replaying errors.
    chosen = []
    for group in groups:
        good = sorted((r for r in group if r['reward'] > 0), key=lambda r: digest(r['fen']))
        bad = sorted((r for r in group if r['reward'] < 0), key=lambda r: digest(r['fen']))
        take = good[:24] + bad[:24]
        used = {id(r) for r in take}
        take.extend(r for r in group if id(r) not in used and len(take) < 48)
        chosen.extend(take)
    return chosen


def fit(paths, initial, out):
    paths, initial, out = list(map(Path, paths)), Path(initial), Path(out)
    identity = dict(source_files={str(p): sha256(p) for p in paths},
        initial_policy_sha256=sha256(initial), trainer_sha256=sha256(__file__),
        epochs=1, learning_rate=0.00005, seed=20260908, anchor_weight=2., max_per_game=48)
    if (out / 'training.json').exists():
        previous = json.loads((out / 'training.json').read_text(encoding='utf-8'))
        if previous['identity'] != identity or previous['status'] not in ('complete', 'no_eligible_examples'):
            raise ValueError('Preserve this training attempt; use a fresh output')
        if previous['status'] == 'complete' and sha256(out / 'player-policy.npz') != previous['model_sha256']:
            raise ValueError('Fitted checkpoint hash mismatch')
        return previous
    if out.exists():
        raise ValueError('Preserve incomplete training attempts; use a fresh output')
    out.mkdir(parents=True)
    write_json(out / 'preparation.json', identity)
    wait_for_capacity(out / 'capacity.json')
    rows = read_examples(paths)
    if not rows:
        result = dict(identity=identity, status='no_eligible_examples', trained=False)
        write_json(out / 'training.json', result)
        return result
    initial_net = Network.load(initial)
    net = Network.load(initial)
    examples = []
    for row in rows:
        board = chess.Board(row['start_fen'])
        for uci in row['history']:
            board.push_uci(uci)
        if board.fen() != row['fen']:
            raise ValueError('Training example history mismatch')
        moves = list(board.legal_moves)
        target = moves.index(chess.Move.from_uci(row['policy_target']))
        features = encode_moves(board, moves)
        anchor = probabilities(initial_net.forward(features)[:, 0]).copy()
        examples.append((features, target, row['policy_weight'], anchor))
    # Preserve the existing broad policy on a small, deterministic old-game replay.
    replay_path = ROOT / 'runs/carlsen-curriculum-20260906/data/curriculum.jsonl'
    replay = []
    if replay_path.exists():
        rng = np.random.default_rng(identity['seed'])
        seen = 0
        with replay_path.open(encoding='utf-8') as source:
            for line in source:
                row = json.loads(line)
                if row['split'] != 'train':
                    continue
                seen += 1
                if len(replay) < 128:
                    replay.append(row['fen'])
                else:
                    index = int(rng.integers(seen))
                    if index < 128:
                        replay[index] = row['fen']
        for fen in replay:
            board = chess.Board(fen)
            moves = list(board.legal_moves)
            if not moves:
                continue
            features = encode_moves(board, moves)
            anchor = probabilities(initial_net.forward(features)[:, 0]).copy()
            examples.append((features, 0, 0., anchor))
    before = sum(reward_loss(initial_net.forward(x)[:, 0], t, w, a)[0]
                 for x, t, w, a in examples) / len(examples)
    optimizer = Adam(net.parameters(), lr=identity['learning_rate'])
    rng = np.random.default_rng(identity['seed'])
    updates = 0
    order = rng.permutation(len(examples))
    for offset in range(0, len(order), 16):
        stop_check()
        indices = order[offset:offset + 16]
        x = np.concatenate([examples[i][0] for i in indices])
        logits = net.forward(x)[:, 0]
        gradients, start = [], 0
        for i in indices:
            features, target, weight, anchor = examples[i]
            count = len(features)
            _, grad = reward_loss(logits[start:start + count], target, weight, anchor)
            gradients.append(grad / len(indices))
            start += count
        gradient = np.concatenate(gradients).reshape(-1, 1)
        if not np.isfinite(gradient).all():
            raise ValueError('Non-finite reward gradient')
        optimizer.zero_grad()
        net.backward(gradient)
        optimizer.step()
        updates += 1
    after = sum(reward_loss(net.forward(x)[:, 0], t, w, a)[0]
                for x, t, w, a in examples) / len(examples)
    model = out / 'player-policy.npz'
    net.save(model)
    result = dict(identity=identity, status='complete', trained=True, updates=updates,
        examples=len(rows), good_examples=sum(r['reward'] > 0 for r in rows),
        corrected_bad_examples=sum(r['reward'] < 0 for r in rows),
        replay_positions=len(replay), replay_source_sha256=sha256(replay_path) if replay else None,
        objective_before=before, objective_after=after, model_sha256=sha256(model),
        architecture=f'{SIZE} inputs / 64 / 32 / 1 move policy', promoted=False,
        selected_agent_changed=False, value_weights_changed=False,
        limitation='One bounded supervised reward-weighted policy update. In-sample objective only; no strength or Elo claim. Quiet descendant labels remain necessary for position-value training.')
    write_json(out / 'training.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reviews', nargs='+', type=Path, required=True)
    parser.add_argument('--initial', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(fit(args.reviews, args.initial, args.out)))
