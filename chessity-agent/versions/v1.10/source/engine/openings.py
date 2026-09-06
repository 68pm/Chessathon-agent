"""Explicit experimental opening repertoire; no player games or engine code.

The Alien Gambit is speculative. This opt-in book is a preference, not a claim
that sacrificing on f7 is best. Black moves are conditions, never our choices.
"""

import chess

ALIEN_LINE = "e4 c6 d4 d5 Nd2 dxe4 Nxe4 Nf6 Ng5 h6 Nxf7 Kxf7 Nf3".split()


def key(board):
    return tuple(board.fen().split()[:4])


def make_book():
    book = {}
    for development in ["Nd2", "Nc3"]:
        line = list(ALIEN_LINE)
        line[4] = development
        board = chess.Board()
        for san in line:
            move = board.parse_san(san)
            if board.turn == chess.WHITE:
                book.setdefault(key(board), move.uci())
            board.push(move)
    return book


ALIEN_BOOK = make_book()


def alien_move(board):
    if board.turn != chess.WHITE or board.fullmove_number > 7 or board.is_game_over():
        return None
    uci = ALIEN_BOOK.get(key(board))
    move = chess.Move.from_uci(uci) if uci else None
    return move if move in board.legal_moves else None
