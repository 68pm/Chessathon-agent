import ast
import importlib.util
import random
from pathlib import Path

import chess
import numpy as np
import pytest

from experiments import daytime_pawn_bitboards_core as core
from scripts.daytime_common import RUN
from training.rule_value import arrays


@pytest.fixture(scope='module')
def original():
    spec = importlib.util.spec_from_file_location('pawn_bits_v154', RUN / 'pawn-extrema-01/prototype/engine/compiled_core.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('count', range(9))
def test_h_file_counts_high_bit_and_multiple(count):
    mask = np.uint64(sum(1 << (r * 8 + 7) for r in range(count)))
    assert core.pawn_file_count(mask, 7) == min(count, 2)
    assert core.pawn_file_count(mask, 0) == 0


def test_random_mirrors_and_all_diagnosed_roots_match(original):
    import json

    roots = json.loads((RUN / 'pawn-bitboards-01/preparation.json').read_text())['roots']
    positions = [chess.Board(r['fen']) for r in roots]
    rng = random.Random(2026090906)
    position = chess.Board()
    for _ in range(700):
        if position.is_game_over(claim_draw=True) or position.ply() >= 180:
            position = chess.Board()
        positions.append(position.copy(stack=False))
        position.push(rng.choice(list(position.legal_moves)))
    for p in positions:
        for board in (p, p.mirror()):
            pieces, state = arrays(board)
            saved = pieces.copy(), state.copy()
            for conversion in (False, True):
                assert core.classical(pieces, state, conversion) == original.classical(pieces, state, conversion), board.fen()
            assert np.array_equal(pieces, saved[0]) and np.array_equal(state, saved[1])


def test_only_classical_and_new_helper_changed():
    before = ast.parse((RUN / 'pawn-extrema-01/prototype/engine/compiled_core.py').read_text())
    after = ast.parse(Path(core.__file__).read_text())
    a = {n.name: ast.dump(n) for n in before.body if isinstance(n, ast.FunctionDef)}
    b = {n.name: ast.dump(n) for n in after.body if isinstance(n, ast.FunctionDef)}
    assert b.keys() - a.keys() == {'pawn_file_count'}
    assert all(a[k] == b[k] for k in a if k != 'classical')
