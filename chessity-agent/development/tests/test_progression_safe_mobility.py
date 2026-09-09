import ast
import importlib.util
import random
from pathlib import Path
import chess
import numpy as np
import pytest
from experiments import progression_safe_mobility_core as core
from scripts.progression_common import BASE
from training.rule_value import arrays


@pytest.fixture(scope='module')
def original():
    spec = importlib.util.spec_from_file_location('safe_mobility_control', BASE / 'engine/compiled_core.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def check(board, original):
    pieces, state = arrays(board)
    saved = pieces.copy(), state.copy()
    phase = min(24, sum(len(board.pieces(p, c)) * w
        for p, w in ((2, 1), (3, 1), (4, 2), (5, 4)) for c in (True, False)))
    adjustment = 0.
    for colour in (True, False):
        attacked = set()
        for pawn in board.pieces(chess.PAWN, not colour):
            attacked.update(board.attacks(pawn))
        for p in (2, 3, 4, 5):
            count = sum(sq in attacked and board.color_at(sq) != colour
                for origin in board.pieces(p, colour) for sq in board.attacks(origin))
            adjustment -= (1 if colour else -1) * count * ((3 if p in (2, 3) else 1) * phase + 2 * (24 - phase)) / 24
        for target in chess.SQUARES:
            encoded = chess.square_rank(target) * 16 + chess.square_file(target)
            assert core.enemy_pawn_controls(pieces, encoded, 1 if colour else -1) == (target in attacked)
    before = original.classical(pieces, state)
    after = core.classical(pieces, state)
    # Original and adjusted scores round their complete tapered sums independently.
    assert abs(after - before - adjustment * (1 if board.turn else -1)) <= 1.000001
    assert np.array_equal(pieces, saved[0]) and np.array_equal(state, saved[1])


FENS = [chess.STARTING_FEN, 'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1',
    '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2',
    '7k/P7/6K1/8/8/8/8/8 w - - 0 1',
    '4k3/8/3p4/4N3/8/8/8/4K3 w - - 0 1',
    '4k3/8/p6p/8/3Q4/8/8/4K3 w - - 0 1',
    '4k3/8/8/p6p/3B4/8/8/4K3 w - - 0 1',
    '4k3/8/8/8/4R3/3p4/8/4K3 b - - 0 1']


@pytest.mark.parametrize('fen', FENS)
def test_independent_attack_map_and_tapered_adjustment(fen, original):
    board = chess.Board(fen)
    assert board.is_valid()
    for b in (board, board.mirror()):
        check(b, original)


def test_random_positions_and_colour_symmetry(original):
    rng = random.Random(2026090920)
    board = chess.Board()
    for _ in range(160):
        check(board, original)
        check(board.mirror(), original)
        a = core.classical(*arrays(board)); b = core.classical(*arrays(board.mirror()))
        assert a == b
        if board.is_game_over(claim_draw=True):
            board = chess.Board()
        else:
            board.push(rng.choice(list(board.legal_moves)))


def test_only_mobility_evaluation_changed():
    a = ast.parse((BASE / 'engine/compiled_core.py').read_text())
    b = ast.parse(Path(core.__file__).read_text())
    old = {n.name: ast.dump(n) for n in a.body if isinstance(n, ast.FunctionDef)}
    new = {n.name: ast.dump(n) for n in b.body if isinstance(n, ast.FunctionDef)}
    assert set(new) - set(old) == {'enemy_pawn_controls'}
    assert all(old[key] == new[key] for key in old if key != 'classical')
