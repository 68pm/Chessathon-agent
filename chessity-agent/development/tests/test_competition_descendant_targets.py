"""Guard label perspective, history exclusions and unclipped residuals."""
import chess

from training.competition_descendant_targets import classify, export


def leaf(board, scores=(350, 380), base=100):
    return dict(id='leaf-test', target='competition-r1-ply-10', start_fen=board.root().fen(),
        history=[m.uci() for m in board.move_stack], fen=board.fen(), root_white=True,
        terminal=False, static_root=base, origins=[dict(kind='counterfactual')],
        quiescence=dict(complete=True, score_root=base),
        teacher=[dict(cp=cp, mate=None, cp_root=cp * (1 if board.turn else -1)) for cp in scores])


def test_black_descendant_uses_its_own_value_and_does_not_clip():
    board = chess.Board('6k1/pp3ppp/8/8/8/8/PP3PPP/6K1 b - - 0 1')
    row = classify(leaf(board, scores=(-800, -830), base=50))
    assert row['eligible_static_target'] and row['static_stm_cp'] == -50
    assert row['required_residual_stm_cp'] == [-750, -780]
    assert not row['within_500cp_range'] and not row['trained']


def test_identical_piece_input_repetition_is_not_a_static_training_target():
    board = chess.Board('6k1/pp3ppp/8/8/8/8/PP3PPP/6K1 w - - 0 1')
    first = classify(leaf(board))
    for uci in ['g1f1', 'g8f8', 'f1g1', 'f8g8']:
        board.push_uci(uci)
    repeated = classify(leaf(board))
    assert first['sparse_features_768'] == repeated['sparse_features_768']
    assert first['eligible_static_target'] and not repeated['eligible_static_target']
    assert any('history-sensitive' in why for why in repeated['excluded_reasons'])


def test_unstable_and_mate_labels_stay_explicitly_excluded():
    board = chess.Board('6k1/pp3ppp/8/8/8/8/PP3PPP/6K1 w - - 0 1')
    assert not classify(leaf(board, scores=(0, 200)))['eligible_static_target']
    item = leaf(board)
    item['teacher'] = [dict(cp=None, mate=-4), dict(cp=None, mate=-3)]
    row = classify(item)
    assert not row['eligible_static_target'] and row['required_residual_stm_cp'] is None


def test_export_preserves_duplicate_audit_without_double_training_weight(tmp_path):
    import json

    board = chess.Board('6k1/pp3ppp/8/8/8/8/PP3PPP/6K1 w - - 0 1')
    a, b = leaf(board), leaf(board)
    b['id'] = 'leaf-duplicate'
    source = tmp_path / 'teacher.json'
    source.write_text(json.dumps(dict(status='complete', leaves=[a, b])))
    report = export(source, tmp_path / 'export')
    assert report['records'] == 2 and report['eligible_static_targets'] == 1
    rows = [json.loads(s) for s in (tmp_path / 'export/independent-descendants.jsonl').read_text().splitlines()]
    assert rows[1]['duplicate_of'] == rows[0]['id'] and not rows[1]['trained']


def test_pending_recapture_is_not_mistaken_for_a_static_evaluation_error():
    board = chess.Board('6k1/pp3ppp/8/8/8/8/PP3PPP/6K1 w - - 0 1')
    item = leaf(board, scores=(0, 10), base=-1000)
    item['quiescence'] = dict(complete=True, score_root=0)
    row = classify(item)
    assert row['required_residual_stm_cp'] == [1000, 1010]
    assert not row['eligible_static_target']
    assert any('unresolved tactics' in why for why in row['excluded_reasons'])
