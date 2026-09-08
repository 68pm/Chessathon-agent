"""Local network arithmetic, actual descendant values and context guards."""
import ast
import json
from pathlib import Path

import chess
import numpy as np

from experiments import e55_local_value_core as core
from experiments.aspiration_driver import arrays
from training.local_descendant_value import pattern_parameters

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/e55-local-value-20260908'


def parameters():
    with np.load(OUT / 'prototype/models/value.npz', allow_pickle=False) as data:
        return data['weights'], data['bias'], data['output']


def test_hidden_features_equal_independent_hamming_distance():
    rng = np.random.default_rng(20260908)
    centres = (rng.random((32,768)) < .03).astype(np.float32)
    w,b = pattern_parameters(centres)
    samples = np.vstack([centres,centres.copy()])
    samples[32:,0:4] = 1 - samples[32:,0:4]
    actual = np.clip(samples @ w + b,0,1)
    expected = np.maximum(0,1-np.count_nonzero(samples[:,None,:] != centres[None,:,:],axis=2)/4)
    np.testing.assert_array_equal(actual,expected)


def test_export_and_both_runtime_paths_match_all_independent_descendants():
    w,b,o = parameters()
    fit = json.loads((OUT / 'training.json').read_text())
    for row in fit['records']:
        board = chess.Board(row['fen'])
        pieces,state = arrays(board)
        before = pieces.copy(),state.copy()
        x = np.zeros(768,dtype=np.float32)
        x[row['sparse_features_768']] = 1
        expected = core.classical.py_func(pieces,state) + int(round(float(np.clip(np.clip(x@w+b,0,1)@o,-1500,1500))))
        direct = core.evaluate.py_func(pieces,state,w,b,o,1.,False)
        accum = core.build_accumulator.py_func(pieces,w,b)
        incremental = core.evaluate_accumulator.py_func(pieces,state,o,1.,False,accum)
        assert abs(direct-expected) <= 1 and abs(incremental-expected) <= 1
        assert np.array_equal(pieces,before[0]) and np.array_equal(state,before[1])
    assert fit['fitted_training_mae_cp'] < fit['baseline_training_mae_cp']


def test_hidden_rights_and_draw_clock_disable_even_large_residual():
    w = np.zeros((768,32),dtype=np.float32)
    b = np.ones(32,dtype=np.float32)
    o = np.full(32,100.,dtype=np.float32)
    for fen in ['r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1',
                '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2',
                '4k3/8/8/8/8/8/4P3/4K3 w - - 70 36']:
        pieces,state = arrays(chess.Board(fen))
        base = core.classical.py_func(pieces,state)
        assert core.evaluate.py_func(pieces,state,w,b,o,1.,False) == base
        assert core.evaluate_accumulator.py_func(pieces,state,o,1.,False,core.build_accumulator.py_func(pieces,w,b)) == base


def test_range_is_bounded_and_zero_network_is_exact_baseline():
    pieces,state = arrays(chess.Board('4k3/8/8/8/8/8/4P3/4K3 w - - 0 1'))
    w = np.zeros((768,32),dtype=np.float32)
    b = np.ones(32,dtype=np.float32)
    base = core.classical.py_func(pieces,state)
    for value, expected in [(0,0),(100,1500),(-100,-1500)]:
        o = np.full(32,value,dtype=np.float32)
        assert core.evaluate.py_func(pieces,state,w,b,o,1.,False) - base == expected


def test_every_search_value_call_uses_repetition_guard():
    tree = ast.parse(Path(core.__file__).read_text())
    search = next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='search')
    calls = [n for n in ast.walk(search) if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='evaluate_accumulator']
    assert len(calls)==2 and all(n.args[3].id=='effective_blend' for n in calls)
    assignment = next(n for n in ast.walk(search) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='effective_blend' for t in n.targets))
    for repetitions in [1,2,3]:
        expression = ast.Expression(assignment.value)
        assert eval(compile(expression,'<guard>','eval'),{'repetitions':repetitions,'blend':1.}) == (1. if repetitions==1 else 0.)
