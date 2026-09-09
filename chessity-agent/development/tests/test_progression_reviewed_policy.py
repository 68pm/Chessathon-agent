import json
import chess
import numpy as np
import pytest
from engine.player_policy import PlayerPolicy, encode_moves
from nn.model import Network
from scripts.progression_common import RUN, BASE, digest, manifest

OUT = RUN / 'reviewed-policy-01'


@pytest.mark.parametrize('index', range(12))
def test_runtime_matches_training_forward_and_bounded_legal_preferences(index):
    prep = json.loads((OUT / 'preparation.json').read_text())
    row = prep['roots'][index]; board = chess.Board(row['start_fen'])
    for move in row['history']:
        board.push_uci(move)
    assert board.fen() == row['fen']
    path = OUT / 'prototype/models/player-policy.npz'
    policy, network = PlayerPolicy(path), Network.load(path)
    moves = list(board.legal_moves)
    assert np.allclose(policy.logits(board, moves), network.forward(encode_moves(board, moves))[:, 0], atol=1e-5)
    bonuses = policy.bonuses(board, moves, 40)
    assert set(bonuses) == set(moves) and all(0 <= value <= 40 for value in bonuses.values())
    assert board.fen() == row['fen']


def test_only_fitted_policy_and_bounded_scale_change():
    before, after = manifest(BASE), manifest(OUT / 'prototype')
    assert {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)} == {'models/player-policy.npz', 'runtime.json'}
    assert digest(OUT / 'prototype/models/player-policy.npz') == json.loads((RUN / 'reward-policy-01/state.json').read_text())['model_sha256']
