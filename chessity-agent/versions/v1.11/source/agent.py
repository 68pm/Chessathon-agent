"""AI Chessathon entry point. No network, disk writes, external engines or worker threads."""

import json
import os
import time
from collections import Counter
from pathlib import Path

import chess

from engine.search import Search, position_key
from engine.time_manager import allocate

_root = Path(__file__).resolve().parent
_config_path = _root / "runtime.json"
_config = json.loads(_config_path.read_text()) if _config_path.exists() else {}
_mode = _config.get("mode", "classical")
_opening = None
if _config.get("opening_style") == "alien":
    from engine.openings import alien_move

    _opening = alien_move
_evaluator = None
if _mode != "classical":
    for _variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
        os.environ[_variable] = "1"
    from engine.evaluation import Evaluator
    from engine.neural import NeuralValue

    _evaluator = Evaluator(_mode, NeuralValue(_root / "models" / "value.npz"))
_search = Search(_evaluator, style_tolerance=_config.get("style_tolerance", 0))
_known = Counter()
_last = None


def get_move(fen: str, time_left_ms: int) -> str:
    global _last
    started = time.perf_counter()
    board = chess.Board(fen)
    fallback = next(iter(board.legal_moves), None)
    if fallback is None:
        # No legal UCI move exists; the referee must terminate such a game before calling.
        return "0000"
    if time_left_ms <= 20:
        return fallback.uci()
    if _last is not None:
        # Reconstruct the opponent's one intervening move when it is unambiguous.
        connected = False
        for move in _last.legal_moves:
            _last.push(move)
            matches = _last.fen() == board.fen()
            _last.pop()
            if matches:
                connected = True
                break
        if not connected:
            _known.clear()
    _known[position_key(board)] += 1
    book_move = _opening(board) if _opening else None
    if book_move is not None:
        board.push(book_move)
        _known[position_key(board)] += 1
        _last = board
        return book_move.uci()
    budget = allocate(time_left_ms, board.fullmove_number, board.legal_moves.count())
    overhead = time.perf_counter() - started
    result = _search.run(
        board, max(0, budget.hard - overhead), max(0, budget.soft - overhead), known=_known
    )
    chosen = result.move if result.move in board.legal_moves else fallback
    board.push(chosen)
    _known[position_key(board)] += 1
    _last = board
    return chosen.uci()
