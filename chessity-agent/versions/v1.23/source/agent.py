"""AI Chessathon entry point. No network, disk writes, external engines or worker threads."""

import json
import os
import sys
import time
from collections import Counter
from pathlib import Path

# Inference also avoids bytecode-cache writes when run outside the read-only referee.
sys.dont_write_bytecode = True

import chess

from engine.search import Search, position_key
from engine.time_manager import allocate

_root = Path(__file__).resolve().parent
_config_path = _root / "runtime.json"
_config = json.loads(_config_path.read_text()) if _config_path.exists() else {}
_mode = _config.get("mode", "classical")
_opening = None
_selective_opening = _config.get("opening_style") == "alien-selective"
if _config.get("opening_style") in {"alien", "alien-selective"}:
    from engine.openings import alien_move

    _opening = alien_move
_evaluator = None
if _mode != "classical":
    for _variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
        os.environ[_variable] = "1"
    from engine.evaluation import Evaluator
    from engine.neural import NeuralValue

    _evaluator = Evaluator(_mode, NeuralValue(_root / "models" / "value.npz"))
_policy = None
if _config.get("player_policy"):
    for _variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
        os.environ[_variable] = "1"
    from engine.player_policy import PlayerPolicy

    _policy = PlayerPolicy(_root / "models" / "player-policy.npz")
if _config.get("root_value"):
    if _policy is None or _mode != "classical":
        raise ValueError("Root fusion requires a policy and classical node evaluation")
    from engine.fusion import RootFusion
    from engine.neural import NeuralValue

    _policy = RootFusion(_policy, NeuralValue(_root / "models" / "value.npz"),
                         value_cp=_config.get("root_value_cp", 5))
_search = Search(
    _evaluator,
    style_tolerance=_config.get("style_tolerance", 0),
    player_policy=_policy,
    policy_cp=_config.get("policy_cp", 20),
)
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
    if book_move is not None and not _selective_opening:
        board.push(book_move)
        _known[position_key(board)] += 1
        _last = board
        return book_move.uci()
    adaptive = _config.get("adaptive_time", False)
    if adaptive and board.legal_moves.count() == 1:
        board.push(fallback)
        _known[position_key(board)] += 1
        _last = board
        return fallback.uci()
    budget = allocate(time_left_ms, board.fullmove_number, board.legal_moves.count(),
                      adaptive=adaptive, in_check=board.is_check())
    overhead = time.perf_counter() - started
    result = _search.run(
        board,
        max(0, budget.hard - overhead),
        max(0, budget.soft - overhead),
        known=_known,
        preferred_move=book_move if _selective_opening else None,
        preference_cp=_config.get("alien_cp", 15),
        adaptive_stop=adaptive,
    )
    chosen = result.move if result.move in board.legal_moves else fallback
    board.push(chosen)
    _known[position_key(board)] += 1
    _last = board
    return chosen.uci()
