import time

import chess
import numpy as np

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
