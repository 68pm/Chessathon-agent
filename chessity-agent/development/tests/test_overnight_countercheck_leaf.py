import random

import chess
import numpy as np
import pytest

from experiments import overnight_countercheck_leaf_core as core
from scripts.overnight_geometry_trial import ROOT
from tests.test_overnight_bitsets_fixed import SPECIAL_FENS, decode
from tests.test_overnight_bitsets_fixed import arrays as piece_arrays
from training.rule_value import features


@pytest.fixture(scope='module')
def parameters():
    with np.load(ROOT / 'runs/overnight-20260909/rule-value-01/value.npz', allow_pickle=False) as data:
        return tuple(data[name].copy() for name in ('weights', 'rule_weights', 'bias', 'output'))


def arrays(board):
    pieces, state = piece_arrays(board)
    return pieces, np.append(state, np.int64(board.fullmove_number))


def oracle(board, parameters):
    weights, rules, bias, output = parameters
    x = features(board).astype(np.float64)
    hidden = x @ np.vstack((weights, rules)).astype(np.float64) + bias
    return float(np.clip(hidden, 0, 1) @ output.astype(np.float64))


def verify(position, parameters):
    weights, rules, bias, output = parameters
    board, state = arrays(position)
    before, before_state = board.copy(), state.copy()
    acc = core.build_accumulator(board, weights, bias)
    value = core.rule_residual(board, state, output, rules, acc)
    assert abs(value - oracle(position, parameters)) < .002
    assert core.legal_ep_file(board, state) == (chess.square_file(position.ep_square) if position.has_legal_en_passant() else -1)
    base, phase = core.classical_phase(board, state, False)
    expected = base if position.fullmove_number <= 12 or phase <= 8 else base + round(.5 * max(-600, min(600, value)))
    assert core.evaluate_accumulator(board, state, output, rules, .5, False, acc) == expected
    assert core.evaluate_accumulator(board, state, output, rules, 0., False, acc) == base
    assert np.array_equal(board, before) and np.array_equal(state, before_state)
    return board, state, acc


@pytest.mark.parametrize('fen', SPECIAL_FENS)
def test_special_moves_rules_and_incremental_restoration(fen, parameters):
    weights, rules, bias, output = parameters
    for position in (chess.Board(fen), chess.Board(fen).mirror()):
        position.fullmove_number = 20
        board, state, acc = verify(position, parameters)
        before, before_state, before_acc = board.copy(), state.copy(), acc.copy()
        for move in core.legal_moves(board, state):
            old = core.make(board, state, move)
            core.update_accumulator(acc, weights, move, old, 1)
            child = position.copy(stack=True)
            child.push(decode(int(move)))
            expected_board, expected_state = arrays(child)
            assert np.array_equal(board, expected_board) and np.array_equal(state, expected_state)
            assert np.allclose(acc, core.build_accumulator(board, weights, bias), atol=1e-10, rtol=0)
            assert abs(core.rule_residual(board, state, output, rules, acc) - oracle(child, parameters)) < .002
            core.update_accumulator(acc, weights, move, old, -1)
            core.unmake(board, state, move, old)
            assert np.array_equal(board, before) and np.array_equal(state, before_state)
            assert np.allclose(acc, before_acc, atol=1e-10, rtol=0)


@pytest.mark.parametrize('fullmove', [1, 12, 13, 40])
def test_opening_gate_and_draw_clock_are_exact(fullmove, parameters):
    position = chess.Board()
    position.fullmove_number = fullmove
    for clock in (0, 1, 69, 70, 99):
        position.halfmove_clock = clock
        verify(position, parameters)


def test_pawn_endings_stay_classical(parameters):
    for fen in ('8/7k/8/8/3P4/8/8/4K3 w - - 0 40',
                '4k3/8/8/8/3p4/8/7K/8 b - - 10 50'):
        position = chess.Board(fen)
        assert position.is_valid()
        board, state, acc = verify(position, parameters)
        assert core.evaluate_accumulator(board, state, parameters[3], parameters[1], .5, False, acc) == core.classical(board, state)


def test_seeded_histories_and_mirrors(parameters):
    rng = random.Random(202609090321)
    board = chess.Board()
    for _ in range(240):
        if board.is_game_over(claim_draw=True) or board.ply() >= 180:
            board = chess.Board()
        verify(board, parameters)
        verify(board.mirror(), parameters)
        board.push(rng.choice(list(board.legal_moves)))
    assert core.rule_residual.nopython_signatures
    print('480 seeded/mirrored positions matched the full 781-feature NumPy oracle.')


def test_fullmove_accumulator_long_stack_restores(parameters):
    weights, _, bias, _ = parameters
    position = chess.Board()
    board, state = arrays(position)
    acc = core.build_accumulator(board, weights, bias)
    rng = random.Random(202609090322)
    stack = []
    for _ in range(80):
        if position.is_game_over(claim_draw=True):
            break
        move = rng.choice(list(core.legal_moves(board, state)))
        stack.append((move, board.copy(), state.copy(), acc.copy()))
        old = core.make(board, state, move)
        stack[-1] += (old,)
        core.update_accumulator(acc, weights, move, old, 1)
        position.push(decode(int(move)))
        assert state[6] == position.fullmove_number
    assert len(stack) >= 40
    while stack:
        move, before, before_state, before_acc, old = stack.pop()
        core.update_accumulator(acc, weights, move, old, -1)
        core.unmake(board, state, move, old)
        assert np.array_equal(board, before) and np.array_equal(state, before_state)
        assert np.allclose(acc, before_acc, atol=1e-10, rtol=0)


def search_arguments(board, state, **overrides):
    args = dict(board=board, state=state, depth=0, alpha=-31000, beta=31000,
        ply=1, qdepth=5, hashes=np.asarray([1234, 0], dtype=np.uint64), hlen=1,
        context=np.uint64(123), ttkey=np.zeros(16, dtype=np.uint64),
        ttcontext=np.zeros(16, dtype=np.uint64), ttdata=np.zeros((16, 5), dtype=np.int64),
        killers=np.zeros((100, 2), dtype=np.int64), history=np.zeros((2, 128, 128), dtype=np.int64),
        control=np.asarray([0, 0, 100000]), deadline=float('inf'),
        weights=np.zeros((768, 64)), bias=np.zeros(64), output=np.zeros(64),
        rule_weights=np.zeros((13, 64)), blend=0., conversion=False, reductions=False,
        accumulator=np.zeros((2, 64)), extensions_left=2, quiet_checks_left=4,
        quiet_attacker=-1)
    args.update(overrides)
    return args


@pytest.mark.parametrize('attacker,credits,expected_checks', [(-1, 4, True), (-1, 1, True),
    (-1, 0, False), (0, 4, False), (1, 4, True)])
def test_counterchecks_share_credits_and_exclude_nonchecks(monkeypatch, attacker, credits, expected_checks):
    position = chess.Board('6k1/8/8/1q6/8/8/8/3R2K1 w - - 0 20')
    assert position.is_valid() and not position.is_check()
    board, state = arrays(position)
    before, before_state = board.copy(), state.copy()
    expected = {}
    checks = 0
    for move in position.legal_moves:
        quiet = not position.is_capture(move) and not move.promotion
        checking = position.gives_check(move)
        if quiet and (not expected_checks or not checking):
            continue
        child = position.copy(stack=True)
        child.push(move)
        expected[tuple(arrays(child)[0])] = credits - int(quiet)
        checks += int(quiet and checking)
    assert bool(checks) == expected_checks
    visited = {}
    original = core.search.py_func

    def child(*args):
        visited[tuple(args[0])] = args[-2]
        assert args[-1] == attacker
        return 0

    monkeypatch.setattr(core, 'search', child)
    args = search_arguments(board, state, quiet_attacker=attacker, quiet_checks_left=credits)
    original(**args)
    assert visited == expected
    assert np.array_equal(board, before) and np.array_equal(state, before_state)
    assert args['control'][1] == 0


@pytest.mark.parametrize('fullmove,expected', [(1, 0.), (12, 0.), (13, .5), (40, .5)])
def test_root_scope_passes_effective_blend_without_mutating_configuration(monkeypatch, fullmove, expected):
    from experiments.overnight_countercheck_leaf_driver import CompiledSearch
    seen = []

    def iteration(*args):
        seen.append(args[-3])
        return args[4][0], 0, True

    monkeypatch.setattr(core, 'root_iteration', iteration)
    position = chess.Board()
    position.fullmove_number = fullmove
    search = CompiledSearch(blend=.5)
    before = position.fen()
    result = search.run(position, seconds=5., max_depth=1)
    assert result.move in position.legal_moves and position.fen() == before
    assert seen == [expected] and search.blend == .5


@pytest.mark.parametrize('first,second', [((10, 0., 0, 4), (20, .5, 0, 4)),
    ((5, .5, 0, 4), (10, .5, -1, 4)), ((13, .5, -1, 4), (13, .5, -1, 3))])
def test_cache_separates_activation_and_previously_aliased_check_contexts(monkeypatch, first, second):
    board = np.zeros(142, dtype=np.int64)
    board[4], board[116] = 6, -6
    state = np.asarray([1, 0, -1, 0, 4, 116, first[0]], dtype=np.int64)
    args = search_arguments(board, state, depth=1, blend=first[1],
        quiet_attacker=first[2], quiet_checks_left=first[3])
    mask = (1 << 64) - 1
    key, context = 1234, 123
    quiet = (first[2] + 1) * 5 + first[3] + 1
    neural = min(first[0], 13) if first[1] else 0
    cached = context ^ ((2 * 11400714819323198485) & mask)
    cached ^= (quiet * 15485907386658061715) & mask
    cached ^= (neural * 0xa0761d6478bd642f) & mask
    args['ttkey'][key & 15], args['ttcontext'][key & 15] = key, cached
    args['ttdata'][key & 15] = [5, 12345, 0, 0, 0]
    monkeypatch.setattr(core, 'attacked', lambda *unused: False)
    monkeypatch.setattr(core, 'insufficient', lambda *unused: False)

    def miss(*unused):
        raise LookupError('Fresh search required')

    monkeypatch.setattr(core, 'generate', miss)
    with np.errstate(over='ignore'):
        assert core.search.py_func(**args) == 12345
        state[6] = second[0]
        args.update(blend=second[1], quiet_attacker=second[2], quiet_checks_left=second[3])
        with pytest.raises(LookupError, match='Fresh search required'):
            core.search.py_func(**args)

