import ast
import importlib.util
import time
from pathlib import Path
import chess
import numpy as np
import pytest
from experiments import progression_verification_core as core
from experiments import progression_verification_driver as driver
from scripts.progression_common import BASE
from training.rule_value import arrays


@pytest.fixture(scope='module')
def original():
    spec = importlib.util.spec_from_file_location('verification_reference', BASE / 'engine/compiled_core.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    return module


def root(module, board):
    b, s = arrays(board); saved = b.copy(), s.copy()
    moves = module.legal_moves(b, s); hashes = np.zeros(800, dtype=np.uint64)
    hashes[0] = module.position_hash(b, s)
    result = module.root_iteration(b, s, 2, int(moves[0]), moves, np.zeros(len(moves), dtype=np.int64), hashes, 1,
        np.zeros(1024, dtype=np.uint64), np.zeros(1024, dtype=np.uint64), np.zeros((1024, 5), dtype=np.int64),
        np.zeros((100, 2), dtype=np.int64), np.zeros((2, 128, 128), dtype=np.int64),
        np.array([0, 0, 1000000], dtype=np.int64), time.perf_counter() + 60,
        np.zeros((768, 32), dtype=np.float32), np.zeros(32, dtype=np.float32), np.zeros(32, dtype=np.float32),
        0., False, False, np.empty((100, 512), dtype=np.int64), np.empty((100, 512), dtype=np.int64))
    assert np.array_equal(b, saved[0]) and np.array_equal(s, saved[1])
    return result, moves


@pytest.mark.parametrize('fen', ['8/8/5k2/8/3p4/3K4/8/8 w - - 0 1',
    '8/8/5k2/8/3p4/3K4/8/8 b - - 0 1', '7k/5Q2/6K1/8/8/8/8/8 w - - 0 1',
    '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2', '7k/P7/6K1/8/8/8/8/8 w - - 0 1'])
def test_full_root_result_and_bound_alignment(fen, original):
    board = chess.Board(fen)
    expected, _ = root(original, board); actual, moves = root(core, board)
    assert actual[:3] == expected and actual[2]
    assert actual[1] == max(actual[3])
    assert moves[list(actual[3]).index(max(actual[3]))] == actual[0]


@pytest.mark.parametrize('mode', ['complete', 'incomplete', 'depth_cap', 'clock_empty', 'mate'])
def test_verification_clock_budget_and_fallback(monkeypatch, mode):
    clock = [0.]; calls = []
    monkeypatch.setattr(driver.time, 'perf_counter', lambda: clock[0])
    def iteration(*args):
        moves, previous, depth = args[4], args[3], args[2]
        calls.append(dict(moves=moves.copy(), previous=previous, depth=depth, bonuses=args[5].copy()))
        clock[0] += .2 if mode != 'clock_empty' else (.16 if len(calls) < 3 else .66)
        verification = len(moves) == 3
        scores = np.arange(len(moves), dtype=np.int64)
        if verification:
            assert previous in moves
            if mode == 'incomplete':
                args[13][1] = 1
                return previous, 0, False, scores
            return int(moves[1]), 100, True, scores
        score = 29999 if mode == 'mate' and depth >= 3 else int(scores[-1])
        return int(moves[-1]), score, True, scores
    monkeypatch.setattr(core, 'root_iteration', iteration)
    search = driver.CompiledSearch()
    board = chess.Board(); expected = driver.decode(int(core.legal_moves(*driver.arrays(board))[-1]))
    result = search.run(board, seconds=1., soft=.5, max_depth=3 if mode == 'depth_cap' else 64)
    assert result.move in board.legal_moves and result.elapsed <= 1.05
    if mode in ('depth_cap', 'clock_empty', 'mate'):
        assert result.verified_depth == 0 and all(len(c['moves']) == 20 for c in calls)
    elif mode == 'complete':
        assert result.verified_depth == result.depth + 1 == 4 and result.move != expected
    else:
        assert result.verified_depth == 0 and result.move == expected


def test_internal_evaluation_search_and_rules_unchanged():
    a = ast.parse((BASE / 'engine/compiled_core.py').read_text()); b = ast.parse(Path(core.__file__).read_text())
    old = {n.name: ast.dump(n) for n in a.body if isinstance(n, ast.FunctionDef)}
    new = {n.name: ast.dump(n) for n in b.body if isinstance(n, ast.FunctionDef)}
    assert old.keys() == new.keys()
    assert all(old[key] == new[key] for key in old if key != 'root_iteration')
