"""Independent threat legality and bounded defensive-search control checks."""

import ast
import json
import random
import sys
from pathlib import Path

import chess
import numpy as np
import pytest

from experiments import overnight_queen_defence_core as core
from experiments.hash_driver import arrays
from scripts.overnight_queen_defence import BASE, ROOT, changed_source


def oracle(position):
    king = position.king(position.turn)
    if not any(chess.square_distance(q, king) <= 3 for q in position.pieces(chess.QUEEN, not position.turn)):
        return False, 0
    probe = position.copy(stack=False)
    probe.turn = not position.turn
    probe.ep_square = None
    possible = 0
    for move in probe.generate_pseudo_legal_moves():
        if probe.piece_type_at(move.from_square) == chess.QUEEN:
            df = chess.square_file(move.to_square) - chess.square_file(king)
            dr = chess.square_rank(move.to_square) - chess.square_rank(king)
            possible += int(df == 0 or dr == 0 or abs(df) == abs(dr))
    found = False
    for move in list(probe.legal_moves):
        if probe.piece_type_at(move.from_square) != chess.QUEEN:
            continue
        df = chess.square_file(move.to_square) - chess.square_file(king)
        dr = chess.square_rank(move.to_square) - chess.square_rank(king)
        if df != 0 and dr != 0 and abs(df) != abs(dr):
            continue
        probe.push(move)
        found |= probe.is_check() and not probe.is_attacked_by(position.turn, move.to_square)
        probe.pop()
    return bool(found), possible


def check(position):
    assert position.is_valid() and not position.is_check()
    board, state = arrays(position)
    before, before_state = board.copy(), state.copy()
    expected, candidates = oracle(position)
    answer = bool(core.safe_queen_check_threat(board, state))
    assert not answer or expected
    if candidates <= 12:
        assert answer == expected, position.fen()
    assert np.array_equal(board, before) and np.array_equal(state, before_state)
    return answer, candidates


@pytest.mark.parametrize('fen,expected', [
    ('6k1/8/8/8/6q1/8/5PPP/6K1 w - - 0 1', True),
    ('4k3/8/8/8/8/4q3/4RPPP/6K1 w - - 0 1', False),
    ('7k/8/8/8/8/qN6/P7/K7 w - - 0 1', False),
    ('4k3/8/8/8/8/8/8/4K3 w - - 0 1', False),
    (chess.STARTING_FEN, False),
])
def test_safe_pinned_attacked_blocked_and_absent_queen_checks(fen, expected):
    for position in (chess.Board(fen), chess.Board(fen).mirror()):
        answer, count = check(position)
        assert count <= 12 and answer == expected


def test_compiled_probe_on_seeded_play_and_all_field_roots():
    rng = random.Random(202609090105)
    position = chess.Board()
    checked, positive = 0, 0
    for _ in range(600):
        if position.is_game_over(claim_draw=True) or position.ply() >= 180:
            position = chess.Board()
        if not position.is_check():
            for sample in (position, position.mirror()):
                answer, _ = check(sample)
                checked += 1
                positive += answer
        position.push(rng.choice(list(position.legal_moves)))
    roots = json.loads((ROOT / 'runs/overnight-20260909/bitsets-02/preparation.json').read_text())['roots']
    for row in roots:
        position = chess.Board(row['start_fen'])
        for uci in row['history']:
            position.push_uci(uci)
        assert position.fen() == row['fen']
        if not position.is_check():
            for sample in (position, position.mirror()):
                answer, _ = check(sample)
                checked += 1
                positive += answer
    assert checked >= 800 and positive >= 10
    assert core.safe_queen_check_threat.nopython_signatures
    print(f'Compiled threat oracle: {checked} positions/mirrors, {positive} positive triggers.')


def extract(name):
    source = Path(core.__file__).read_text(encoding='utf-8')
    node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name)
    node.decorator_list = []
    env = {'np': np}
    exec(compile(ast.Module(body=[node], type_ignores=[]), 'defence-control-oracle', 'exec'), env)
    return env


def test_probe_never_tries_more_than_twelve_candidates():
    env = extract('safe_queen_check_threat')
    position = chess.Board('6k1/8/8/8/6q1/8/5PPP/6K1 w - - 0 1')
    board, state = arrays(position)
    before, before_state = board.copy(), state.copy()
    calls = []
    # Deliberately repeat aligned destinations: this exercises the work bound,
    # not move-generation correctness, which the compiled oracle checks above.
    moves = [54 | (6 << 7)] * 30
    def make(pieces, probe, move):
        calls.append(('make', move))
        return 0
    def unmake(pieces, probe, move, old):
        calls.append(('unmake', move))
    env.update(generate=lambda *args: moves, make=make, unmake=unmake,
               attacked=lambda *args: True)
    assert not env['safe_queen_check_threat'](board, state)
    assert len(calls) == 24 and [c[0] for c in calls] == ['make', 'unmake'] * 12
    assert np.array_equal(board, before) and np.array_equal(state, before_state)


def search_control(depth=0, qdepth=0, credit=1, threat=True, aborted=False):
    env = extract('search')
    events = []
    board, state = arrays(chess.Board())
    hashes = np.asarray([1] + [0] * 99, dtype=np.uint64)
    ttkey, ttcontext = np.zeros(2, dtype=np.uint64), np.zeros(2, dtype=np.uint64)
    ttdata = np.zeros((2, 5), dtype=np.int64)
    control = np.asarray([0, int(aborted), 10000], dtype=np.int64)
    def check_threat(*args):
        events.append('threat')
        return threat
    def generate(pieces, position, captures):
        events.append(('captures_only', captures))
        return []
    snapshot = {}
    class CapturedBoundary(Exception):
        pass
    def order_moves(*args):
        frame = sys._getframe(1)
        snapshot.update(depth=frame.f_locals['depth'], context=int(frame.f_locals['tt_context']))
        raise CapturedBoundary
    env.update(attacked=lambda *args: False, insufficient=lambda *args: False,
        has_legal_move=lambda *args: True, evaluate_accumulator=lambda *args: 37,
        queen_near_king=lambda *args: False, safe_queen_check_threat=check_threat,
        generate=generate, order_moves=order_moves)
    try:
        with np.errstate(over='ignore'):
            env['search'](board, state, depth, -1000, 1000, 1, qdepth, hashes, 1,
                np.uint64(0), ttkey, ttcontext, ttdata, None, None, control, float('inf'),
                None, None, None, 0., False, False, None, 2, 4, 0, credit)
    except CapturedBoundary:
        pass
    return events, snapshot.get('depth', 0), snapshot.get('context', 0)


@pytest.mark.parametrize('depth,qdepth,credit,threat,expected_probe,full_width', [
    (0, 0, 1, True, True, True), (0, 2, 1, True, True, True),
    (0, 3, 1, True, False, False), (0, 0, 0, True, False, False),
    (0, 0, 1, False, True, False), (1, 0, 1, True, False, True),
])
def test_one_credit_horizon_and_full_width_defence(depth, qdepth, credit, threat, expected_probe, full_width):
    events, written_depth, _ = search_control(depth, qdepth, credit, threat)
    assert ('threat' in events) == expected_probe
    assert ('captures_only', not full_width) in events
    assert written_depth == int(full_width)


def test_credit_is_consumed_and_transposition_context_keeps_unused_credit_separate():
    _, depth, used_context = search_control(0, 0, 1)
    _, _, no_credit_context = search_control(1, 0, 0)
    _, _, available_context = search_control(1, 0, 1)
    assert depth == 1 and used_context == no_credit_context
    assert available_context != no_credit_context
    assert search_control(aborted=True)[0] == []


def test_only_search_and_new_probe_change_and_credit_reaches_every_recursive_call():
    original = ast.parse((BASE / 'engine/compiled_core.py').read_text(encoding='utf-8'))
    changed = ast.parse(changed_source((BASE / 'engine/compiled_core.py').read_text(encoding='utf-8')))
    def unrelated(tree):
        return [ast.dump(n) for n in tree.body if not (isinstance(n, ast.FunctionDef)
                and n.name in ('search', 'safe_queen_check_threat'))]
    assert unrelated(original) == unrelated(changed)
    search = next(n for n in changed.body if isinstance(n, ast.FunctionDef) and n.name == 'search')
    calls = [n for n in ast.walk(search) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Name) and n.func.id == 'search']
    assert len(calls) == 4 and all(len(n.args) == 28 and n.args[-1].id == 'queen_defences_left' for n in calls)
