import chess
import numpy as np
import pytest

from experiments import overnight_root_bootstrap_core as core
from experiments import overnight_root_bootstrap_driver as driver


def encode(uci):
    move = chess.Move.from_uci(uci)
    return move.from_square // 8 * 16 + move.from_square % 8 + ((move.to_square // 8 * 16 + move.to_square % 8) << 7)


@pytest.mark.parametrize('finished_depth', [False, True])
def test_driver_preserves_last_full_depth_and_counts_bootstrap_work(monkeypatch, finished_depth):
    monkeypatch.setattr(driver.time, 'perf_counter', lambda: 10.)
    calls = []
    board = chess.Board()
    before = board.fen()

    def iteration(*args):
        control = args[13]
        calls.append(dict(depth=args[2], previous=args[3], credit=args[-1], deadline=args[14],
            nodes=int(control[0]), limit=int(control[2])))
        control[0] += 10
        if args[-1] == 0:
            return encode('e2e4'), 20, False
        if len(calls) == 2 and finished_depth:
            return encode('d2d4'), 40, True
        control[1] = 1
        return encode('g1f3'), 1000, False

    monkeypatch.setattr(core, 'root_iteration', iteration)
    search = driver.CompiledSearch()
    result = search.run(board, seconds=1., max_depth=4, max_nodes=10000)
    assert board.fen() == before and not board.move_stack
    assert calls[0]['credit'] == 0 and calls[0]['limit'] == 4096
    assert calls[1]['credit'] == 4 and calls[1]['limit'] == 10000
    assert calls[1]['nodes'] == 10 and calls[1]['previous'] == encode('e2e4')
    assert calls[0]['deadline'] < calls[1]['deadline']
    assert result.nodes == 10 * len(calls)
    assert result.depth == int(finished_depth)
    assert result.move.uci() == ('d2d4' if finished_depth else 'g1f3')


def test_no_finished_child_retains_seed_without_fake_depth(monkeypatch):
    monkeypatch.setattr(driver.time, 'perf_counter', lambda: 10.)
    board = chess.Board()

    def iteration(*args):
        args[13][0] += 5
        args[13][1] = 1
        if args[-1] == 0:
            return encode('e2e4'), 25, False
        return args[3], -31000, False

    monkeypatch.setattr(core, 'root_iteration', iteration)
    result = driver.CompiledSearch().run(board, seconds=1.)
    assert result.move.uci() == 'e2e4' and result.depth == 0 and result.nodes == 10


def test_node_exhaustion_in_seed_does_not_start_more_search(monkeypatch):
    monkeypatch.setattr(driver.time, 'perf_counter', lambda: 10.)
    calls = []

    def iteration(*args):
        calls.append(args[-1])
        args[13][0] = args[13][2]
        args[13][1] = 1
        return encode('e2e4'), 0, False

    monkeypatch.setattr(core, 'root_iteration', iteration)
    result = driver.CompiledSearch().run(chess.Board(), seconds=1., max_nodes=32)
    assert calls == [0] and result.nodes == 32 and result.depth == 0


def test_expired_deadline_keeps_a_legal_move_without_search(monkeypatch):
    monkeypatch.setattr(driver.time, 'perf_counter', lambda: 10.)

    def iteration(*unused):
        raise AssertionError('No search after the deadline')

    monkeypatch.setattr(core, 'root_iteration', iteration)
    board = chess.Board()
    result = driver.CompiledSearch().run(board, seconds=0.)
    assert result.move in board.legal_moves and result.depth == 0 and result.nodes == 0


def test_root_discards_interrupted_child_and_restores_board(monkeypatch):
    position = chess.Board()
    board, state = driver.arrays(position)
    before, oldstate = board.copy(), state.copy()
    moves = np.array([encode('e2e4'), encode('d2d4')], dtype=np.int64)
    calls = []
    control = np.array([0, 0, 1000], dtype=np.int64)

    def child(*args):
        calls.append(args[-2])
        if len(calls) == 2:
            control[1] = 1
            return -9999
        return -42

    monkeypatch.setattr(core, 'search', child)
    value = core.root_iteration.py_func(board, state, 1, int(moves[0]), moves, np.zeros(2, dtype=np.int64),
        np.zeros(10, dtype=np.uint64), 0, np.zeros(16, dtype=np.uint64), np.zeros(16, dtype=np.uint64),
        np.zeros((16, 5), dtype=np.int64), np.zeros((100, 2), dtype=np.int64),
        np.zeros((2, 128, 128), dtype=np.int64), control, float('inf'),
        np.zeros((768, 32)), np.zeros(32), np.zeros(32), 0., False, False, np.int64(0))
    assert value == (encode('e2e4'), 42, False) and calls == [0, 0]
    np.testing.assert_array_equal(board, before)
    np.testing.assert_array_equal(state, oldstate)
