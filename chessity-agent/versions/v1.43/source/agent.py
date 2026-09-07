"""Chessathon agent: original compiled search; all learning happens offline."""

import json
import os
import platform
import sys
import time
from pathlib import Path

sys.dont_write_bytecode = True
for _name in ['OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMBA_NUM_THREADS']:
    os.environ[_name] = '1'
os.environ['NUMBA_DISABLE_INTEL_SVML'] = '1'
if sys.platform == 'win32':
    # Numba asks platform.machine(). This CPython's Windows uname fallback runs
    # a shell command. Populate its standard cache from read-only OS information
    # instead, retaining the strict no-subprocess/no-socket inference contract.
    _winver = sys.getwindowsversion()
    _machine = os.environ.get('PROCESSOR_ARCHITEW6432', os.environ.get('PROCESSOR_ARCHITECTURE', 'AMD64'))
    platform._uname_cache = platform.uname_result(
        'Windows', '', str(_winver.major), f'{_winver.major}.{_winver.minor}.{_winver.build}', _machine)

import chess
from engine.compiled_driver import CompiledSearch

from engine.openings import alien_move
from engine.player_policy import PlayerPolicy
from engine.time_manager import allocate

_root = Path(__file__).resolve().parent
_config = json.loads((_root / 'runtime.json').read_text())
_opening = alien_move
_policy = PlayerPolicy(_root / 'models/player-policy.npz') if _config.get('player_policy') else None
_search = CompiledSearch(_policy, _config.get('policy_cp', 10),
                         conversion=_config.get('conversion', False),
                         reductions=_config.get('reductions', False),
                         model=_root / 'models/value.npz' if _config.get('residual_value') else None,
                         blend=_config.get('value_blend', 0.0))
_search.warmup()
_endgames = None
if _config.get('elementary_tables'):
    from engine.elementary_endgames import ElementaryEndgames

    _endgames = ElementaryEndgames(_root / 'tables', _config.get('table_max_pieces', 3))
_last = None


def get_move(fen: str, time_left_ms: int) -> str:
    global _last
    started = time.perf_counter()
    board = chess.Board(fen)
    fallback = next(iter(board.legal_moves), None)
    if fallback is None:
        return '0000'
    if time_left_ms <= 20:
        return fallback.uci()
    if _last is not None:
        for move in list(_last.legal_moves):
            _last.push(move)
            if _last.fen() == fen:
                board = _last.copy(stack=True)
                _last.pop()
                break
            _last.pop()
    if _endgames is not None:
        solved = _endgames.choose(board)
        if solved is not None:
            board.push(solved)
            _last = board
            return solved.uci()
    budget = allocate(time_left_ms, board.fullmove_number, board.legal_moves.count())
    overhead = time.perf_counter() - started
    preferred = alien_move(board) if _config.get('opening_style') == 'alien-selective' else None
    result = _search.run(board, max(0, budget.hard - overhead), max(0, budget.soft - overhead),
                         preferred_move=preferred, preference_cp=_config.get('alien_cp', 15))
    chosen = result.move if result.move in board.legal_moves else fallback
    board.push(chosen)
    _last = board
    return chosen.uci()
