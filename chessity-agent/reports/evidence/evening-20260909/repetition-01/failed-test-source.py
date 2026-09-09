import ast
import random
from pathlib import Path
import chess
import numpy as np
import pytest
from experiments import evening_repetition_core as core
from scripts.evening_common import ROOT
from training.rule_value import arrays

def verify(board):
    replay=board.root()
    hashes=[int(core.position_hash(*arrays(replay)))]
    for move in board.move_stack:
        replay.push(move)
        hashes.append(int(core.position_hash(*arrays(replay))))
    for start in (0,max(0,len(hashes)-8),max(0,len(hashes)-13)):
        keys=np.array(hashes[start:],dtype=np.uint64)
        full=sum(k==keys[-1] for k in keys[max(0,len(keys)-board.halfmove_clock-1):])>=3
        assert core.threefold(keys,len(keys),board.halfmove_clock)==full
    assert core.threefold(np.array(hashes,dtype=np.uint64),len(hashes),board.halfmove_clock)==board.is_repetition(3)

@pytest.mark.parametrize('seed',range(6))
def test_legal_history_prefixes(seed):
    rng=random.Random(2026090960+seed)
    board=chess.Board()
    for _ in range(120):
        verify(board)
        if board.is_game_over(claim_draw=True):board=chess.Board()
        else:board.push(rng.choice(list(board.legal_moves)))

@pytest.mark.parametrize('fen,moves',[
    (chess.STARTING_FEN,['g1f3','g8f6','f3g1','f6g8']*4),
    ('7k/8/8/8/8/8/P7/K7 w - - 0 1',['a1b1','h8g8','b1a1','g8h8']*3),
    (chess.STARTING_FEN,['g1f3','g8f6','f3g1','f6g8']*2+['e2e4','e7e5']+['g1f3','g8f6','f3g1','f6g8']*2),
    ('r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1',['e1g1','e8c8','g1h1','c8b8','h1g1','b8c8']+['g1h1','c8b8','h1g1','b8c8']*2),
    ('7k/8/8/3pP3/8/8/8/4K3 w - d6 0 1',['e5d6','h8g8','e1f1','g8h8','f1e1']+['h8g8','e1f1','g8h8','f1e1']*2),
])
def test_repetitions_and_irreversible_boundaries(fen,moves):
    board=chess.Board(fen)
    verify(board)
    for move in moves:
        board.push_uci(move)
        verify(board)

def test_side_key_disjoint_and_ep_legality():
    assert int(core.ZSIDE)>>63==1
    assert int(core.ZPIECE.max())<2**63 and int(core.ZCASTLE.max())<2**63 and int(core.ZEP.max())<2**63
    for fen in ['7k/8/8/3pP3/8/8/8/4K3 w - d6 0 1',
                '4r2k/8/8/3pP3/8/8/8/4K3 w - d6 0 1']:
        board=chess.Board(fen)
        pieces,state=arrays(board)
        original=pieces.copy(),state.copy()
        key=int(core.position_hash(pieces,state))
        state[2]=-1
        without=int(core.position_hash(pieces,state))
        assert (key!=without)==board.has_legal_en_passant()
        assert np.array_equal(pieces,original[0])

def test_only_repetition_query_changes():
    before=ast.parse((ROOT/'runs/daytime-20260909/move-buffers-01/prototype/engine/compiled_core.py').read_text())
    after=ast.parse(Path(core.__file__).read_text())
    a={n.name:ast.dump(n) for n in before.body if isinstance(n,ast.FunctionDef)}
    b={n.name:ast.dump(n) for n in after.body if isinstance(n,ast.FunctionDef)}
    assert b.keys()-a.keys()=={'threefold'}
    assert all(a[k]==b[k] for k in a if k!='search')
