"""Full-evaluation parity for the original evaluator's passed-pawn optimisation."""
import ast
import importlib.util
import random
from pathlib import Path

import chess
import numpy as np
import pytest

from experiments import daytime_pawn_extrema_core as core
from experiments.hash_driver import arrays
from scripts.daytime_pawn_extrema_transform import transform

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('pawn_extrema_reference42', ROOT / 'candidates/compiled-reductions-v1/engine/compiled_core.py')
reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reference)


@pytest.mark.parametrize('seed', range(10))
def test_seeded_positions_and_mirrors_preserve_full_evaluation(seed):
    rng = random.Random(2026090910 + seed)
    position = chess.Board()
    for _ in range(100):
        if position.is_game_over(claim_draw=True):
            position = chess.Board()
        for board in (position, position.mirror()):
            pieces, state = arrays(board)
            before = pieces.copy(), state.copy()
            for conversion in (False, True):
                assert core.classical(pieces,state,conversion) == reference.classical(pieces,state,conversion)
            assert np.array_equal(pieces,before[0]) and np.array_equal(state,before[1])
        position.push(rng.choice(list(position.legal_moves)))


@pytest.mark.parametrize('fen', [
    '7k/8/8/8/P7/8/8/7K w - - 0 1',
    '7k/8/p7/8/P7/8/8/7K w - - 0 1',
    '7k/8/1p6/8/P7/8/8/7K w - - 0 1',
    '7k/8/8/8/P7/p7/8/7K w - - 0 1',
    '7k/8/7p/8/6P1/6P1/8/K7 w - - 0 1',
])
def test_file_edges_doubled_blocked_and_passed_pawns(fen):
    position=chess.Board(fen)
    assert position.is_valid()
    for board in (position,position.mirror()):
        args=arrays(board)
        assert core.classical(*args) == reference.classical(*args)


def test_only_classical_function_changes():
    parent=(ROOT / 'candidates/compiled-reductions-v1/engine/compiled_core.py').read_text()
    assert ast.dump(ast.parse(Path(core.__file__).read_text())) == ast.dump(ast.parse(transform(parent)))
