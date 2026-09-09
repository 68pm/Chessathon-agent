"""Bounded replay of verified good moves and corrections, anchored to v1.56."""
import os
for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS'):
    os.environ[name] = '1'
import json
from pathlib import Path
import chess
import numpy as np
from nn.model import Network
from nn.optim import Adam
from engine.player_policy import encode_moves
from training.reward_policy import read_examples, probabilities, reward_loss
from scripts.progression_common import ROOT, RUN, BASE, check_stop, digest, save
from scripts.feedback_matches_windows import feedback_path
from scripts.overnight_portable_fast_screen import audit_feedback
from scripts.overnight_capacity import wait_for_capacity

OUT = RUN / 'reward-policy-01'


def run():
    check_stop()
    assert not OUT.exists()
    wait_for_capacity(RUN / 'reward-policy-capacity.json', minimum_memory_mb=1400, wait_seconds=120)
    trials = ['e9-king-step-buffers-01-versus56-b12', 'e9-king-step-buffers-01-versus56-d48',
              'p9-v156-development2400-01']
    paths = []
    for trial in trials:
        kind = 'rated' if trial.startswith('p9-') else 'comparison'
        root = ROOT / 'runs/improvement-loop-20260907' / trial / (kind + '-prototype')
        audit_feedback(root / 'results.json')
        feedback = feedback_path(root / 'postgame-feedback')
        markers = sorted((feedback / 'completed').glob('*.json'))
        assert len(markers) == 2
        paths += [feedback / json.loads(path.read_text())['review'] for path in markers]
    rows = read_examples(paths)
    initial = BASE / 'models/player-policy.npz'
    anchor, network = Network.load(initial), Network.load(initial)
    examples = []
    for row in rows:
        board = chess.Board(row['start_fen'])
        for uci in row['history']:
            board.push_uci(uci)
        assert board.fen() == row['fen']
        moves = list(board.legal_moves); target = moves.index(chess.Move.from_uci(row['policy_target']))
        x = encode_moves(board, moves)
        examples.append((x, target, row['policy_weight'], probabilities(anchor.forward(x)[:, 0])))
    assert sum(row['reward'] > 0 for row in rows) >= 24 and sum(row['reward'] < 0 for row in rows) >= 12
    # Replay remains anchored to the original broad policy throughout all eight passes.
    replay_path = ROOT / 'runs/carlsen-curriculum-20260906/data/curriculum.jsonl'
    rng = np.random.default_rng(2026090921)
    replay, count = [], 0
    with replay_path.open(encoding='utf-8') as stream:
        for line in stream:
            row = json.loads(line)
            if row['split'] != 'train':
                continue
            count += 1
            if len(replay) < 128:
                replay.append(row['fen'])
            else:
                index = int(rng.integers(count))
                if index < 128:
                    replay[index] = row['fen']
    for fen in replay:
        board = chess.Board(fen); moves = list(board.legal_moves)
        if moves:
            x = encode_moves(board, moves)
            examples.append((x, 0, 0., probabilities(anchor.forward(x)[:, 0])))
    OUT.mkdir()
    save(OUT / 'preparation.json', dict(reviews={str(p): digest(p) for p in paths},
        source_sha256=digest(Path(__file__)), initial_policy_sha256=digest(initial),
        replay_source_sha256=digest(replay_path), epochs=8, learning_rate=.0003,
        anchor_weight=2., seed=2026090921, planned_runtime_policy_cp=40,
        scope='Root preference only. Eight bounded supervised reward passes, fixed original-policy '
              'anchor and broad replay. No Elo-weighted rewards, leaf-value labels or automatic promotion.'))
    def objective():
        return float(np.mean([reward_loss(network.forward(x)[:, 0], target, weight, reference)[0]
            for x, target, weight, reference in examples]))
    before = objective(); optimizer = Adam(network.parameters(), lr=.0003)
    epochs, updates = [], 0
    for epoch in range(8):
        order = rng.permutation(len(examples))
        for start in range(0, len(order), 16):
            check_stop()
            chosen = [examples[i] for i in order[start:start + 16]]
            x = np.concatenate([e[0] for e in chosen]); logits = network.forward(x)[:, 0]
            gradients, offset = [], 0
            for features, target, weight, reference in chosen:
                count = len(features)
                _, gradient = reward_loss(logits[offset:offset + count], target, weight, reference)
                gradients.append(gradient / len(chosen)); offset += count
            grad = np.concatenate(gradients).reshape(-1, 1)
            assert np.isfinite(grad).all()
            optimizer.zero_grad(); network.backward(grad); optimizer.step(); updates += 1
        epochs.append(dict(epoch=epoch + 1, objective=objective()))
    network.save(OUT / 'player-policy.npz')
    result = dict(status='complete', passed=False, objective_before=before,
        objective_after=epochs[-1]['objective'], epochs=epochs, updates=updates,
        training_objective_improved=epochs[-1]['objective'] < before,
        policy_examples=len(rows), good=sum(r['reward'] > 0 for r in rows),
        corrections=sum(r['reward'] < 0 for r in rows), broad_replay=len(replay),
        model_sha256=digest(OUT / 'player-policy.npz'),
        decision='needs_frozen_quality_and_match_gates', promoted=False)
    save(OUT / 'state.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'epochs'}), flush=True)


if __name__ == '__main__':
    run()
