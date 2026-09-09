import ast
import random
from pathlib import Path
import chess
import numpy as np
import pytest
from experiments import evening_pawn_threat_core as core
from scripts.evening_common import ROOT
from training.rule_value import arrays

def verify_moves(board):
    for move in list(board.legal_moves):
        piece=board.piece_at(move.from_square)
        side=1 if board.turn else -1
        board.push(move)
        target=chess.square_rank(move.to_square)*16+chess.square_file(move.to_square)
        expected=(piece.piece_type==chess.PAWN and
            (chess.square_rank(move.to_square)==(6 if piece.color else 1) or
            any(board.color_at(sq)==(not piece.color) for sq in chess.SquareSet(chess.BB_PAWN_ATTACKS[piece.color][move.to_square]))))
        pieces,state=arrays(board)
        saved=pieces.copy()
        assert bool(core.pawn_threat_after_move(pieces,target,side,piece.piece_type*side))==expected
        assert np.array_equal(pieces,saved)
        board.pop()

@pytest.mark.parametrize('seed',range(8))
def test_pawn_threats_match_independent_attacks(seed):
    board=chess.Board()
    rng=random.Random(2026090970+seed)
    for _ in range(50):
        verify_moves(board)
        if board.is_game_over():board=chess.Board()
        else:board.push(rng.choice(list(board.legal_moves)))

@pytest.mark.parametrize('fen',[
    '6k1/4rppp/1pB5/3p4/P2P4/R1P2bP1/5P1P/5K2 b - - 0 23',
    '7k/8/P7/8/8/7p/8/K7 w - - 0 1',
    '7k/8/8/3pP3/8/8/8/4K3 w - d6 0 1',
])
def test_edge_files_promotion_and_recent_position(fen):
    board=chess.Board(fen)
    verify_moves(board)
    verify_moves(board.mirror())

def test_change_scope():
    import json
    prep=json.loads((ROOT/'runs/evening-20260909/pawn-threat-01/preparation.json').read_text())
    before=ast.parse((ROOT/prep['parent']/'engine/compiled_core.py').read_text())
    after=ast.parse(Path(core.__file__).read_text())
    a={n.name:ast.dump(n) for n in before.body if isinstance(n,ast.FunctionDef)}
    b={n.name:ast.dump(n) for n in after.body if isinstance(n,ast.FunctionDef)}
    assert b.keys()-a.keys()=={'pawn_threat_after_move'}
    assert all(a[k]==b[k] for k in a if k!='search')
