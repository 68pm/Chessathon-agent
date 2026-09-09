"""Synthetic data-safety regressions; no engines or candidate compilation."""

import copy
import hashlib

import chess
import pytest

from scripts.feedback_position_plan import plan
from training.game_feedback import grade, phase


def make_review(colour=chess.WHITE, fullmove=20, scores=None, mirror=False):
    start = chess.Board()
    start.fullmove_number = fullmove
    sequence = 'e2e4 e7e5 g1f3 b8c6 f1b5 a7a6 b5a4 g8f6 e1g1 f8e7'.split()
    if mirror:
        start = start.mirror()
        colour = not colour
        sequence = [chess.Move(chess.square_mirror(chess.Move.from_uci(m).from_square),
            chess.square_mirror(chess.Move.from_uci(m).to_square)).uci() for m in sequence]
    board = start.copy(stack=True)
    rows = []
    for ply, uci in enumerate(sequence):
        if board.turn == colour:
            best_cp, gap = (scores or {}).get(ply, (200, 0))
            best_move = next(m.uci() for m in board.legal_moves if m.uci() != uci) if gap >= 70 else uci

            def continuation(first):
                child = board.copy(stack=True)
                pv = [first]
                child.push_uci(first)
                for _ in range(3):
                    if child.is_game_over():
                        break
                    move = sorted(child.legal_moves, key=lambda m: m.uci())[0]
                    pv.append(move.uci())
                    child.push(move)
                return pv

            labels = [dict(nodes=n, best=dict(cp=best_cp, mate=None, pv=continuation(best_move)),
                played=dict(cp=best_cp-gap, mate=None, pv=continuation(uci))) for n in (80000, 320000)]
            reward = grade(labels, uci, board.legal_moves.count())
            tags = [phase(board)]
            if reward['reward'] == 1 and best_cp - gap >= 150:
                tags.append('preserves_estimated_advantage')
            rows.append(dict(ply=ply, fullmove=board.fullmove_number, white=board.turn,
                start_fen=start.fen(), history=sequence[:ply], fen=board.fen(),
                played=uci, san=board.san(chess.Move.from_uci(uci)), labels=labels, tags=tags, **reward))
        board.push_uci(uci)
    game = dict(start_fen=start.fen(), moves=sequence, candidate_white=colour, score=0.,
        candidate_version='synthetic-test-only', source_game_id=str(colour), opponent='synthetic-2400')
    game['game_key'] = hashlib.sha256(repr(game).encode()).hexdigest()
    return dict(status='complete', own_moves=len(rows), identity=dict(game=game), rows=rows)


def test_earliest_recoverable_error_beats_already_lost_larger_error():
    review = make_review(scores={0: (-700, 500), 2: (-100, 80), 4: (200, 250), 6: (200, 90)})
    result = plan([('synthetic.json', review)])
    roots = result['summaries'][0]['selected_roots']
    assert [r['ply'] for r in roots if r['reward'] < 0] == [2, 4, 6]
    assert roots[0]['reason'] == 'first_recoverable_error'
    assert result['summaries'][0]['phase_counts']['middlegame']['negative'] == 4
    assert result['targets'] and len(result['targets']) <= 20
    assert all(r['target_stm_cp'] is None for r in result['targets'])
    assert {r['split'] for r in result['targets']} == {'validation'}


@pytest.mark.parametrize('change', ['running', 'missing_move', 'wrong_history', 'wrong_reward', 'wrong_budgets'])
def test_incomplete_or_corrupt_review_is_rejected(change):
    review = make_review()
    if change == 'running':
        review['status'] = 'running'
    elif change == 'missing_move':
        review['rows'].pop()
        review['own_moves'] -= 1
    elif change == 'wrong_history':
        review['rows'][1]['history'] = []
    elif change == 'wrong_reward':
        review['rows'][0]['reward'] = -1.
    else:
        review['rows'][0]['labels'][0]['nodes'] = 1
    with pytest.raises(AssertionError):
        plan([('synthetic.json', review)])


def test_outcome_and_rating_never_select_or_label_positions():
    original = make_review(scores={2: (-100, 100)})
    changed = copy.deepcopy(original)
    changed['identity']['game'].update(score=1., opponent='synthetic-3000')
    before = plan([('synthetic.json', original)])
    after = plan([('synthetic.json', changed)])
    assert before['targets'] == after['targets']
    assert before['summaries'][0]['selected_roots'] == after['summaries'][0]['selected_roots']
    assert before['summaries'][0]['score'] != after['summaries'][0]['score']


def test_colour_pair_and_mirrored_start_stay_in_one_group():
    documents = [('white.json', make_review()), ('black.json', make_review(colour=False)),
                 ('mirror.json', make_review(mirror=True))]
    result = plan(documents)
    assert len(result['groups']) == 1
    assert {r['split'] for r in result['summaries']} == {'validation'}
    assert len({r['duplicate_key'] for r in result['targets']}) == len(result['targets'])


def test_prior_training_or_label_collisions_cannot_enter_diagnostic():
    docs = [('synthetic.json', make_review(scores={2: (0, 120)}))]
    first = plan(docs)
    assert first['targets']
    second = plan(docs, {r['duplicate_key'] for r in first['targets']})
    assert not second['targets'] and second['maximum_teacher_nodes'] == 0
    assert any(r['reason'] == 'prior_label_or_model_training_collision' for r in second['exclusions'])


def test_opening_root_remains_inactive_when_descendant_crosses_move12():
    result = plan([('synthetic.json', make_review(fullmove=12, scores={0: (0, 100)}))])
    targets = [r for r in result['targets'] if r['root_ply'] == 0]
    assert targets and any(chess.Board(r['fen']).fullmove_number > 12 for r in targets)
    assert all(not r['guarded_residual_active'] for r in targets)


def test_duplicate_game_is_rejected_instead_of_doubling_training_weight():
    review = make_review()
    with pytest.raises(AssertionError):
        plan([('one.json', review), ('two.json', review)])
