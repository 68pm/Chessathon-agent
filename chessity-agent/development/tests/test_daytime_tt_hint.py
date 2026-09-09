"""Guard against foreign-history scores and verify hint-only behaviour."""
import ast
import importlib.util
import time
from pathlib import Path

import chess
import numpy as np
import pytest

from experiments import daytime_tt_hint_core as core
from scripts.daytime_common import RUN
from training.rule_value import arrays


def call(module,position,wrong_context=False,wrong_clock=False,illegal_hint=False,
         seed=True,maximum=100000,depth=2,uci=None):
    board,state=arrays(position)
    saved=board.copy(),state.copy()
    key=np.uint64(module.position_hash(board,state))
    hashes=np.zeros(800,dtype=np.uint64)
    hashes[0]=key
    keys=np.zeros(4096,dtype=np.uint64)
    contexts=np.zeros(4096,dtype=np.uint64)
    data=np.zeros((4096,5),dtype=np.int64)
    slot=int(key)&4095
    if seed:
        keys[slot]=key
        contexts[slot]=np.uint64(int(key)^int(wrong_context))
        hint=123456789 if illegal_hint else module.legal_moves(board,state)[-1]
        if uci:
            move=chess.Move.from_uci(uci)
            hint=module.encode_move((move.from_square//8)*16+move.from_square%8,
                (move.to_square//8)*16+move.to_square%8)
        data[slot]=[20,12345,0,hint,state[3]+int(wrong_clock)]
    weights=np.zeros((768,32),dtype=np.float32)
    bias=np.zeros(32,dtype=np.float32)
    output=np.zeros(32,dtype=np.float32)
    killers=np.zeros((100,2),dtype=np.int64)
    history=np.zeros((2,128,128),dtype=np.int64)
    control=np.array([0,0,maximum],dtype=np.int64)
    accumulator=module.build_accumulator(board,weights,bias)
    score=module.search(board,state,depth,-31000,31000,0,0,hashes,1,key,
        keys,contexts,data,killers,history,control,time.perf_counter()+30,
        weights,bias,output,0.0,False,False,accumulator)
    assert np.array_equal(board,saved[0]) and np.array_equal(state,saved[1])
    return score,control,hashes


@pytest.mark.parametrize('wrong_context,wrong_clock,illegal_hint',[
    (True,False,False),(False,True,False),(True,True,False),
    (True,False,True),(False,False,False),
])
def test_foreign_history_score_cannot_cut_off(wrong_context,wrong_clock,illegal_hint):
    position=chess.Board('7k/8/5KQ1/8/8/8/8/8 w - - 8 1')
    score,control,_=call(core,position,wrong_context,wrong_clock,illegal_hint)
    assert score==(29999 if wrong_context or wrong_clock else 12345)
    assert control[1]==0


@pytest.mark.parametrize('wrong_context,wrong_clock',[(True,False),(False,True),(True,True)])
def test_foreign_hint_is_searched_first_but_cannot_supply_its_score(wrong_context,wrong_clock):
    position=chess.Board()
    score,control,hashes=call(core,position,wrong_context,wrong_clock,
        maximum=2,depth=1,uci='g1f3')
    assert score==0 and control[1]==1 and control[0]==2
    position.push_uci('g1f3')
    assert hashes[1]==core.position_hash(*arrays(position))


@pytest.fixture(scope='module')
def original():
    spec=importlib.util.spec_from_file_location('tt_hint_parent',
        RUN/'fast-legal-01/prototype/engine/compiled_core.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize('fen',[
    chess.STARTING_FEN,
    '4k3/pp3ppp/2n5/3pp3/3PP3/2N5/PPP2PPP/4K3 w - - 0 15',
    '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1',
    'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1',
])
def test_completed_full_width_score_matches_parent(fen,original):
    position=chess.Board(fen)
    a=call(original,position,seed=False,maximum=1000000)
    b=call(core,position,seed=False,maximum=1000000)
    assert a[1][1]==b[1][1]==0 and a[0]==b[0]


def test_only_search_hint_guard_changed():
    before=ast.parse((RUN/'fast-legal-01/prototype/engine/compiled_core.py').read_text())
    after=ast.parse(Path(core.__file__).read_text())
    a={n.name:ast.dump(n) for n in before.body if isinstance(n,ast.FunctionDef)}
    b={n.name:ast.dump(n) for n in after.body if isinstance(n,ast.FunctionDef)}
    assert a.keys()==b.keys() and all(a[k]==b[k] for k in a if k!='search')
