import ast
import importlib.util
import json
import random
from pathlib import Path

import chess
import numpy as np
import pytest

from experiments import daytime_piece_square_core as core
from scripts.daytime_common import RUN
from training.rule_value import arrays


@pytest.fixture(scope='module')
def original():
    spec=importlib.util.spec_from_file_location('piece_square_v155',RUN/'pawn-bitboards-01/prototype/engine/compiled_core.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compare(board,original):
    for position in (board,board.mirror()):
        pieces,state=arrays(position)
        saved=pieces.copy(),state.copy()
        for conversion in (False,True):
            assert core.classical(pieces,state,conversion)==original.classical(pieces,state,conversion),position.fen()
        assert np.array_equal(pieces,saved[0]) and np.array_equal(state,saved[1])


@pytest.mark.parametrize('seed',range(10))
def test_random_legal_continuations_and_colour_mirrors_match(seed,original):
    rng=random.Random(2026090916+seed)
    board=chess.Board()
    for _ in range(120):
        compare(board,original)
        if board.is_game_over(claim_draw=True):
            board=chess.Board()
        else:
            board.push(rng.choice(list(board.legal_moves)))


def test_diagnosed_roots_promotions_en_passant_and_castling(original):
    roots=json.loads((RUN/'piece-square-01/preparation.json').read_text())['roots']
    for row in roots:
        compare(chess.Board(row['fen']),original)
    for fen in ('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1',
                '7k/P7/8/8/8/8/7p/4K3 w - - 0 1',
                '7k/8/8/3pP3/8/8/8/4K3 w - d6 0 1'):
        board=chess.Board(fen)
        compare(board,original)
        for move in list(board.legal_moves):
            board.push(move)
            compare(board,original)
            board.pop()


def test_all_other_search_rule_and_value_functions_are_unchanged():
    before=ast.parse((RUN/'pawn-bitboards-01/prototype/engine/compiled_core.py').read_text())
    after=ast.parse(Path(core.__file__).read_text())
    a={n.name:ast.dump(n) for n in before.body if isinstance(n,ast.FunctionDef)}
    b={n.name:ast.dump(n) for n in after.body if isinstance(n,ast.FunctionDef)}
    assert b.keys()-a.keys()=={'build_piece_square_tables'}
    assert all(a[k]==b[k] for k in a if k!='classical')
