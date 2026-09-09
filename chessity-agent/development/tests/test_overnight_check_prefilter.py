"""Independent legal-check coverage and preservation of all non-quiescence moves."""

import ast
import copy
import random

import chess
import numpy as np
import pytest

from experiments import overnight_check_prefilter_core as core
from experiments.hash_driver import arrays
from scripts.overnight_check_prefilter import BASE, changed_source


def encode(position, move):
    source = chess.square_rank(move.from_square) * 16 + chess.square_file(move.from_square)
    target = chess.square_rank(move.to_square) * 16 + chess.square_file(move.to_square)
    flag = 1 if position.is_en_passant(move) else 2 if position.is_castling(move) else 0
    if position.piece_type_at(move.from_square) == chess.PAWN and abs(target - source) == 32:
        flag = 4
    return source | (target << 7) | ((move.promotion or 0) << 14) | (flag << 17)


def verify(position):
    board, state = arrays(position)
    before, before_state = board.copy(), state.copy()
    quiet, skipped, checking, count = 0, 0, 0, 0
    for move in list(position.legal_moves):
        possible = bool(core.may_give_check(board, state, encode(position, move)))
        gives = position.gives_check(move)
        assert not gives or possible, (position.fen(), move.uci())
        if not position.is_capture(move) and not move.promotion:
            quiet += 1
            skipped += not possible
        checking += gives
        count += 1
    assert np.array_equal(board, before) and np.array_equal(state, before_state)
    return quiet, skipped, checking, count


@pytest.mark.parametrize('fen', [
    '5k2/8/8/8/8/8/8/R3K2R w KQ - 0 1',
    '8/8/8/R4pPk/8/8/8/4K3 w - f6 0 1',
    'k7/8/8/8/8/B7/8/R3K3 w - - 0 1',
    '6k1/8/5P2/8/8/8/8/4K3 w - - 0 1',
    '6k1/8/2N5/8/8/8/8/4K3 w - - 0 1',
    '4k3/P7/8/8/8/8/8/4K3 w - - 0 1',
])
def test_special_and_discovered_checks_are_never_discarded(fen):
    for board in (chess.Board(fen), chess.Board(fen).mirror()):
        assert board.is_valid()
        _, _, checks, _ = verify(board)
        assert checks > 0


def test_seeded_legal_moves_have_no_false_negative_checks_and_keep_state_pure():
    rng = random.Random(202609090204)
    position = chess.Board()
    totals = np.zeros(4, dtype=np.int64)
    for _ in range(300):
        if position.is_game_over(claim_draw=True) or position.ply() >= 160:
            position = chess.Board()
        for board in (position, position.mirror()):
            totals += verify(board)
        position.push(rng.choice(list(position.legal_moves)))
    quiet, skipped, checks, total = map(int, totals)
    assert quiet > 5000 and skipped > quiet // 4 and checks > 100
    assert core.may_give_check.nopython_signatures
    print(f'Checked {total} legal moves; all {checks} checking moves retained; {skipped}/{quiet} quiet moves safely excluded.')


def guard_node(tree):
    search = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'search')
    loop = next(n for n in search.body if isinstance(n, ast.For)
                and isinstance(n.target, ast.Name) and n.target.id == 'index')
    guard = next(n for n in loop.body if isinstance(n, ast.If)
        and any(isinstance(c, ast.Call) and isinstance(c.func, ast.Name) and c.func.id == 'may_give_check'
                for c in ast.walk(n)))
    return loop, guard


@pytest.mark.parametrize('quiescence,checked,quiet,quiet_checks,possible,retained', [
    (False, False, True, False, False, True),
    (True, True, True, False, False, True),
    (True, False, False, True, False, True),
    (True, False, True, True, True, True),
    (True, False, True, True, False, False),
    (True, False, True, False, True, False),
])
def test_guard_preserves_main_search_captures_checks_and_evasions(quiescence, checked, quiet, quiet_checks, possible, retained):
    source = changed_source((BASE / 'engine/compiled_core.py').read_text(encoding='utf-8'))
    _, guard = guard_node(ast.parse(source))
    tree = ast.parse('def keep():\n    for i in range(1):\n        return True\n    return False\n')
    tree.body[0].body[0].body.insert(0, copy.deepcopy(guard))
    env = dict(quiescence=quiescence, checked=checked, quiet=quiet, quiet_checks=quiet_checks,
               board=None, state=None, move=None, may_give_check=lambda *args: possible)
    ast.fix_missing_locations(tree)
    exec(compile(tree, 'quiescence-guard-oracle', 'exec'), env)
    assert env['keep']() == retained


def test_move_order_and_all_existing_logic_remain_unchanged():
    original = (BASE / 'engine/compiled_core.py').read_text(encoding='utf-8')
    before, after = ast.parse(original), ast.parse(changed_source(original))
    loop, guard = guard_node(after)
    loop.body.remove(guard)
    after.body = [n for n in after.body if not (isinstance(n, ast.FunctionDef) and n.name == 'may_give_check')]
    assert ast.dump(before) == ast.dump(after)
