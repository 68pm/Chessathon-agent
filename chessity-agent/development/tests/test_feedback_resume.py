import json
from pathlib import Path

import pytest

from scripts import feedback_matches
from training.game_feedback import review_game, write_json


class TestTeacher:
    __test__ = False
    identity = {'fixture': 'legal deterministic teacher; no strength claim'}
    requested_nodes = 0

    def analyse(self, board, nodes, move=None):
        selected = move or next(iter(board.legal_moves))
        return dict(cp=10 if move is None else 0, mate=None,
                    pv=[selected.uci()], nodes=nodes, depth=1)


@pytest.mark.parametrize('white, expected', [(True, 4), (False, 3)])
def test_every_own_move_reviewed_in_both_win_and_loss(tmp_path, white, expected):
    pgn = '[Result "1-0"]\n\n1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0'
    path = review_game(dict(pgn=pgn, candidate_white=white), tmp_path, TestTeacher())
    data = json.loads(path.read_text(encoding='utf-8'))
    assert data['status'] == 'complete' and data['own_moves'] == expected
    assert data['identity']['game']['score'] == float(white)
    assert all(len(row['labels']) == 2 for row in data['rows'])
    assert all(row['static_value_target'] is None for row in data['rows'])


def test_draw_review_keeps_repetition_context_out_of_policy_fit(tmp_path):
    pgn = '[Result "1/2-1/2"]\n\n1. Nf3 Nf6 2. Ng1 Ng8 3. Nf3 Nf6 4. Ng1 Ng8 1/2-1/2'
    path = review_game(dict(pgn=pgn, candidate_white=True), tmp_path, TestTeacher())
    data = json.loads(path.read_text(encoding='utf-8'))
    assert data['own_moves'] == 4
    assert data['rows'][-1]['policy_target'] is None
    assert data['rows'][-1]['policy_weight'] == 0
    assert len(data['rows'][-1]['history']) == 6


def test_saved_game_does_not_retrain_when_replay_pool_grows(tmp_path, monkeypatch):
    calls = []

    def review(records, out):
        path = Path(out) / 'games/one/review.json'
        write_json(path, {'status': 'complete'})
        calls.append('review')
        return [path]

    def fit(paths, initial, out):
        write_json(Path(out) / 'training.json', {'status': 'complete'})
        calls.append('fit')

    monkeypatch.setattr(feedback_matches, 'review_batch', review)
    monkeypatch.setattr(feedback_matches, 'fit', fit)
    row = dict(pgn='[Result "1/2-1/2"]\n\n1. Nf3 Nf6 1/2-1/2',
               candidate_white=True, candidate_path='fixture')
    first = feedback_matches.learn_after_game(row, tmp_path)
    write_json(tmp_path / 'postgame-feedback/reviews/games/two/review.json', {'status': 'complete'})
    second = feedback_matches.learn_after_game(row, tmp_path)
    assert first == second and calls == ['review', 'fit']
    checkpoint = next((tmp_path / 'postgame-feedback/checkpoints').glob('*/training.json'))
    checkpoint.write_text('changed')
    with pytest.raises(ValueError, match='checkpoint changed'):
        feedback_matches.learn_after_game(row, tmp_path)
