"""Bounds, history restoration, and completed-iteration fallback for cycle17."""
import ast
import time
from pathlib import Path

import chess
import numpy as np
import pytest

from experiments import aspiration_core as core
from experiments import aspiration_oracle as reference
from experiments.aspiration_driver import CompiledSearch, arrays, decode


@pytest.fixture(scope='module', autouse=True)
def compiled_before_position_deadlines():
    # Compilation belongs to startup, not the mathematical bound-test clock.
    CompiledSearch().run(chess.Board(),seconds=float('inf'),soft=float('inf'),
        max_depth=1,max_nodes=4096)


def root(board, depth, alpha=-31000, beta=31000, bonuses=None, nodes=10000000, reference=None):
    search = CompiledSearch()
    pieces, state = arrays(board)
    before, saved = pieces.copy(), state.copy()
    moves = core.legal_moves(pieces, state)
    if bonuses is None:
        bonuses = np.zeros(len(moves), dtype=np.int64)
    else:
        bonuses = np.array([bonuses.get(decode(int(m)).uci(), 0) for m in moves], dtype=np.int64)
    hashes = np.zeros(800, dtype=np.uint64)
    replay, past = board.copy(stack=True), []
    for _ in range(min(board.halfmove_clock, len(board.move_stack)) + 1):
        b, s = arrays(replay)
        past.append(core.position_hash(b, s))
        if not replay.move_stack:
            break
        replay.pop()
    past.reverse()
    hashes[:len(past)] = past
    control = np.array([0, 0, nodes], dtype=np.int64)
    args = (pieces, state, depth, int(moves[0]), moves, bonuses,
        hashes, len(past), search.ttkey, search.ttcontext, search.ttdata, search.killers,
        search.history, control, time.perf_counter() + 120, search.weights, search.bias,
        search.output, 0.0, False, False)
    result = reference.root_iteration(*args) if reference else core.root_iteration(*args, alpha, beta)
    assert np.array_equal(pieces, before) and np.array_equal(state, saved)
    assert list(hashes[:len(past)]) == past
    return result


@pytest.mark.parametrize('fen', [
    chess.STARTING_FEN,
    'r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1',
    '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1',
    '4k3/P7/8/8/8/8/1p6/4K3 w - - 0 1',
    '7k/8/5KQ1/8/8/8/8/8 w - - 0 1',
])
def test_windows_return_valid_bounds_and_restore_state(fen):
    board = chess.Board(fen)
    bonuses = {move.uci(): (i % 6) * 5 for i, move in enumerate(board.legal_moves)}
    _, exact, completed = root(board, 3, bonuses=bonuses)
    assert completed
    _, middle, done = root(board, 3, exact - 10, exact + 10, bonuses)
    assert done and middle == exact
    _, low, done = root(board, 3, exact + 20, exact + 40, bonuses)
    assert done and exact <= low <= exact + 20
    _, high, done = root(board, 3, exact - 40, exact - 20, bonuses)
    assert done and exact - 20 <= high <= exact


def test_repetition_history_is_retained():
    board = chess.Board()
    for move in ['g1f3','g8f6','f3g1','f6g8','g1f3','g8f6','f3g1']:
        board.push_uci(move)
    move = chess.Move.from_uci('f6g8')
    bonus = {move.uci(): 25}
    _, exact, completed = root(board, 3, bonuses=bonus)
    assert completed
    assert root(board, 3, exact - 10, exact + 10, bonus)[1] == exact


def test_driver_widens_but_never_commits_an_incomplete_iteration(monkeypatch):
    calls = []
    def fake(*args):
        depth, previous, control, alpha, beta = args[2], args[3], args[13], args[-2], args[-1]
        calls.append((depth, alpha, beta))
        control[0] += 1
        if depth < 4:
            return previous, 10, True
        if depth == 4:
            return previous, 200, True
        return previous, 0, False
    monkeypatch.setattr(core, 'root_iteration', fake)
    search = CompiledSearch()
    result = search.run(chess.Board(), seconds=30, max_depth=5)
    assert result.depth == 4 and result.score == 200
    assert [x[1:] for x in calls if x[0] == 4] == [(-30,50),(-150,170),(-630,650)]
    assert search.iterations[-1]['completed'] is False


def test_node_limit_and_mate_score_ignore_preferences():
    board = chess.Board('7k/8/5KQ1/8/8/8/8/8 w - - 0 1')
    move, score, complete = root(board, 2, bonuses={m.uci():25 for m in board.legal_moves})
    assert complete and score == 29999
    board.push(decode(int(move)))
    assert board.is_checkmate()
    assert root(chess.Board(), 5, nodes=1024)[2] is False


def test_full_window_preserves_selected_engine_scores():
    path = Path(__file__).resolve().parents[1] / 'candidates/compiled-qsearch-endgames-v1/engine/compiled_core.py'
    # The oracle is the original root function and shares the identical unchanged
    # inner search. Loading a second recursive JIT module in this process failed
    # symbol resolution on this Windows runtime in preserved attempt1.
    original = {node.name:ast.dump(node) for node in ast.parse(path.read_text()).body
        if isinstance(node,ast.FunctionDef)}
    oracle_path = Path(reference.__file__)
    oracle = next(node for node in ast.parse(oracle_path.read_text()).body
        if isinstance(node,ast.FunctionDef) and node.name == 'root_iteration')
    assert ast.dump(oracle) == original['root_iteration']
    changed = {node.name:ast.dump(node) for node in ast.parse(Path(core.__file__).read_text()).body
        if isinstance(node,ast.FunctionDef)}
    assert {k:v for k,v in changed.items() if k != 'root_iteration'} == {
        k:v for k,v in original.items() if k != 'root_iteration'}
    for fen in [chess.STARTING_FEN,
        '2bqr1k1/1pp3b1/6pp/1P1p4/3P2pP/Q3PNP1/3N2P1/5RK1 w - - 0 23',
        '4R3/5bP1/5K2/8/prpk4/8/8/8 b - - 15 56']:
        board = chess.Board(fen)
        bonuses = {m.uci(): (i % 6) * 5 for i, m in enumerate(board.legal_moves)}
        assert root(board, 3, bonuses=bonuses) == root(board, 3, bonuses=bonuses, reference=reference)
