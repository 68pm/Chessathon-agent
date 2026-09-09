import ast
import importlib.util
import time
from pathlib import Path
import chess
import numpy as np
import pytest
from experiments import progression_pv_guard_core as core
from scripts.progression_common import BASE
from training.rule_value import arrays


@pytest.fixture(scope='module')
def original():
    spec = importlib.util.spec_from_file_location('pv_guard_control', BASE / 'engine/compiled_core.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FENS = ['8/8/5k2/8/3p4/3K4/8/8 w - - 0 1',
        '8/8/5k2/8/3p4/3K4/8/8 b - - 0 1',
        '7k/5Q2/6K1/8/8/8/8/8 w - - 0 1',
        '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2',
        '7k/P7/6K1/8/8/8/8/8 w - - 0 1',
        '8/8/8/2k5/8/1K6/1R6/8 b - - 0 1']


def run(module, board, depth=2, budget=10**7, bonus=0):
    pieces, state = arrays(board)
    saved = pieces.copy(), state.copy()
    moves = module.legal_moves(pieces, state)
    hashes = np.zeros(800, dtype=np.uint64)
    hashes[0] = module.position_hash(pieces, state)
    bonuses = np.arange(len(moves), dtype=np.int64) % (bonus + 1)
    control = np.array([0, 0, budget], dtype=np.int64)
    result = module.root_iteration(pieces, state, depth, int(moves[0]), moves, bonuses, hashes, 1,
        np.zeros(1024, dtype=np.uint64), np.zeros(1024, dtype=np.uint64),
        np.zeros((1024, 5), dtype=np.int64), np.zeros((100, 2), dtype=np.int64),
        np.zeros((2, 128, 128), dtype=np.int64), control, time.perf_counter() + 60,
        np.zeros((768, 32), dtype=np.float32), np.zeros(32, dtype=np.float32),
        np.zeros(32, dtype=np.float32), 0., False, False,
        np.empty((100, 512), dtype=np.int64), np.empty((100, 512), dtype=np.int64))
    assert np.array_equal(pieces, saved[0]) and np.array_equal(state, saved[1])
    return result, control


@pytest.mark.parametrize('fen', FENS)
def test_full_window_oracle_and_mirrors(fen, original):
    board = chess.Board(fen)
    assert board.is_valid()
    for b in (board, board.mirror()):
        a, _ = run(original, b)
        actual, _ = run(core, b)
        assert actual == a and actual[2]


@pytest.mark.parametrize('bonus', [1, 10, 25])
def test_policy_adjusted_cutoffs(bonus, original):
    board = chess.Board(FENS[0])
    assert run(core, board, bonus=bonus)[0] == run(original, board, bonus=bonus)[0]


def test_interruption_does_not_report_completed_iteration():
    result, control = run(core, chess.Board(FENS[0]), budget=1)
    assert not result[2] and control[1] and result[1] == 0


def test_only_internal_search_changed():
    before = ast.parse((BASE / 'engine/compiled_core.py').read_text())
    after = ast.parse(Path(core.__file__).read_text())
    a = {node.name: ast.dump(node) for node in before.body if isinstance(node, ast.FunctionDef)}
    b = {node.name: ast.dump(node) for node in after.body if isinstance(node, ast.FunctionDef)}
    assert a.keys() == b.keys()
    assert all(a[key] == b[key] for key in a if key != 'search')
