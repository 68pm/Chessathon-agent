import chess

from scripts.improvement_phase_report import PHASES, error_signals, phase_details, summarise


def score(cp=None, mate=None):
    return dict(cp=cp, mate=mate)


def row(best, played, second=None):
    pair = dict(best=best, played=played)
    return dict(verification=[pair, second or pair])


def test_phase_boundaries_use_material_before_move_number():
    board = chess.Board()
    board.fullmove_number = 12
    assert phase_details(board) == dict(phase='opening', material_phase=24, fullmove=12)
    board.fullmove_number = 13
    assert phase_details(board)['phase'] == 'middlegame'
    ending = chess.Board('8/8/4b3/4K2p/2k4P/5P2/1B6/8 b - - 13 1')
    assert phase_details(ending) == dict(phase='endgame', material_phase=2, fullmove=1)


def test_already_lost_is_distinct_from_first_losing_transition():
    first = error_signals(row(score(-50), score(-400)))
    assert first['large_cp_error'] and first['losing_transition']
    later = error_signals(row(score(-500), score(-900)))
    assert later['large_cp_error'] and not later['losing_transition']
    unstable = error_signals(row(score(-50), score(-400), dict(best=score(-50), played=score(-120))))
    assert not unstable['large_cp_error'] and not unstable['losing_transition']
    assert not error_signals(row(score(-199), score(-200)))['losing_transition']


def test_mate_scores_and_squandered_advantage_are_not_zero_cp():
    mate = error_signals(row(score(mate=5), score(mate=-6)))
    assert mate['mate_loss_transition'] and mate['losing_transition'] and mate['squandered_advantage']
    assert mate['mate_scored'] and not mate['large_cp_error']
    won = error_signals(row(score(300), score(50)))
    assert won['squandered_advantage'] and not won['losing_transition']
    changing = error_signals(row(score(0), score(mate=-5), dict(best=score(0), played=score(mate=5))))
    assert changing['mate_scored'] and not changing['mate_loss_transition'] and not changing['losing_transition']


def test_early_warning_not_relabelled_as_terminal_endgame():
    exposure = {p: dict(own_moves=10, large_cp_errors=int(p == 'opening'), mate_scored=0) for p in PHASES}
    game = dict(opponent='stockfish:2400', score=0, first_warning=dict(phase='opening'),
                first_losing_transition=dict(phase='opening'), first_squandered_advantage=None,
                terminal=dict(phase='endgame'), phase_exposure=exposure)
    unresolved = dict(game, first_warning=None, first_losing_transition=None)
    other = dict(game, opponent='stockfish:2600')
    result = summarise([game, unresolved, other])
    assert result['stockfish:2400']['loss_first_warning_phase']['opening'] == 1
    assert result['stockfish:2400']['loss_first_warning_phase']['unresolved'] == 1
    assert result['stockfish:2400']['loss_terminal_phase'] == dict(endgame=2)
    assert result['stockfish:2600']['games'] == 1
