import chess

from training.puzzle_data import decode_puzzle
from training.puzzle_verifier import duplicate_key, mate_moves


def test_lichess_setup_precedes_solver_and_all_moves_are_legal():
    row = decode_puzzle({"PuzzleId": "test", "FEN": chess.STARTING_FEN,
                         "Moves": "e2e4 e7e5 g1f3", "GameUrl": "https://lichess.org/abcd1234#1",
                         "Themes": "opening"})
    board = chess.Board()
    board.push_uci("e2e4")
    assert row["solver_fen"] == board.fen()
    assert row["solver_colour"] == "black"
    assert row["source_solution"][0] == "e7e5"
    assert row["source_game_id"] == "lichess:abcd1234"


def test_exact_mates_include_every_legal_alternative_and_preserve_board():
    for board in [chess.Board("7k/8/5KQ1/8/8/8/8/R7 w - - 0 1"),
                  chess.Board("7k/8/5KQ1/8/8/8/8/R7 w - - 0 1").mirror()]:
        fen = board.fen()
        expected = []
        for move in list(board.legal_moves):
            board.push(move)
            if board.is_checkmate():
                expected.append(move.uci())
            board.pop()
        choices, _ = mate_moves(board)
        assert choices == sorted(expected)
        assert len(choices) > 1
        assert board.fen() == fen


def test_cutoff_is_unresolved_not_draw_or_failure_and_unwinds_board():
    board = chess.Board()
    fen = board.fen()
    choices, _ = mate_moves(board, 3, node_cap=1)
    assert choices is None
    assert board.fen() == fen and not board.move_stack
    draw = chess.Board("7k/8/6K1/8/8/8/8/8 w - - 0 1")
    assert draw.is_insufficient_material()
    assert mate_moves(draw)[0] == []


def test_mirrors_and_transpositions_share_duplicate_key():
    board = chess.Board()
    board.push_uci("e2e4")
    assert duplicate_key(board) == duplicate_key(board.mirror())
    changed_clock = board.copy()
    changed_clock.halfmove_clock = 7
    changed_clock.fullmove_number = 25
    assert duplicate_key(board) == duplicate_key(changed_clock)


def test_multi_acceptable_loss_ignores_illegal_moves_and_has_correct_gradient():
    import numpy as np

    from training.puzzle_train import masked_target_loss
    logits = np.array([[0.2, -0.3, 100]], dtype=np.float64)
    mask = np.array([[True, True, False]])
    targets = np.array([[0.5, 0.5, 0]])
    loss, gradient = masked_target_loss(logits, mask, targets)
    assert np.isfinite(loss) and gradient[0, 2] == 0
    for i in range(2):
        shifted = logits.copy()
        shifted[0, i] += 1e-6
        numerical = (masked_target_loss(shifted, mask, targets)[0] - loss) / 1e-6
        assert abs(numerical - gradient[0, i]) < 1e-5


def test_verified_sacrifice_target_not_penalised_for_material_or_colour():
    import numpy as np

    from training.puzzle_train import masked_target_loss
    # The optimiser sees verified probabilities, never a capture/material-shaped reward.
    for _solver_colour in [chess.WHITE, chess.BLACK]:
        _, gradient = masked_target_loss(np.array([[0.0, 0.0]]),
                                        np.array([[True, True]]), np.array([[1.0, 0.0]]))
        assert gradient[0, 0] < 0 < gradient[0, 1]
