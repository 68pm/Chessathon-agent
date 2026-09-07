import copy

import chess

from training.counterfactual_value import assess_pair, branch_position, root_pov_scores


def row(board, best, played):
    return dict(start_fen=board.root().fen(), history=[m.uci() for m in board.move_stack],
                fen=board.fen(), played=played[0],
                verification=[dict(best=dict(pv=best), played=dict(pv=played))])


def test_successor_restores_full_repetition_history():
    board = chess.Board()
    for uci in ['g1f3', 'g8f6', 'f3g1', 'f6g8']:
        board.push_uci(uci)
    before = board.fen()
    endpoint, reason = branch_position(row(board, ['e2e4'], ['d2d4']), 'best')
    assert reason is None and endpoint['branch_plies'] == 1
    assert endpoint['board'].root().fen() == chess.STARTING_FEN
    assert len(endpoint['board'].move_stack) == 5
    endpoint['board'].pop()
    assert endpoint['board'].fen() == before and board.fen() == before


def test_check_continuation_and_different_endpoint_perspectives():
    board = chess.Board('4k3/8/8/8/8/8/R7/6K1 w - - 0 1')
    record = row(board, ['a2e2', 'e8d8'], ['a2b2'])
    best, reason = branch_position(record, 'best')
    played, other_reason = branch_position(record, 'played')
    assert reason is other_reason is None
    assert best['branch_plies'] == 2 and played['branch_plies'] == 1
    assert not best['board'].is_check() and best['board'].turn == board.turn
    assert played['board'].turn != board.turn
    analysis = [dict(cp=200, mate=None), dict(cp=220, mate=None)]
    assert root_pov_scores(analysis, best['board'].turn, board.turn) == [200, 220]
    assert root_pov_scores(analysis, played['board'].turn, board.turn) == [-200, -220]


def test_only_stable_preserved_branch_order_accepted():
    branches = dict(best=dict(analysis=[dict(cp=-300, mate=None), dict(cp=-320, mate=None)], root_pov_cp=[300, 320]),
                    played=dict(analysis=[dict(cp=-50, mate=None), dict(cp=-70, mate=None)], root_pov_cp=[50, 70]))
    assert assess_pair(branches, dict(best=300, played=50)) == (True, None)
    mate = copy.deepcopy(branches)
    mate['best']['analysis'][1] = dict(cp=None, mate=2)
    assert assess_pair(mate, dict(best=300, played=50))[0] is False
    reversed_order = copy.deepcopy(branches)
    reversed_order['best']['root_pov_cp'] = [50, 70]
    assert assess_pair(reversed_order, dict(best=50, played=50))[0] is False


def test_terminal_successor_is_quarantined():
    board = chess.Board('7k/8/5KQ1/8/8/8/8/8 w - - 0 1')
    endpoint, reason = branch_position(row(board, ['g6g7'], ['g6h6']), 'best')
    assert endpoint is None and reason == 'terminal endpoint'
