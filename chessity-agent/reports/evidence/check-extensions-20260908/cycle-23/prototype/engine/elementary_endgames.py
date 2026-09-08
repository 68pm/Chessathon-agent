"""Original root selection using permitted Syzygy elementary endgame data."""

import chess.syzygy


class ElementaryEndgames:
    def __init__(self, directory):
        self.tables = chess.syzygy.open_tablebase(str(directory), max_fds=16)

    def close(self):
        self.tables.close()

    def choose(self, board):
        if board.castling_rights or len(board.piece_map()) > 3:
            return None
        choices, uncertain = [], False
        for move in list(board.legal_moves):
            board.push(move)
            try:
                outcome = board.outcome(claim_draw=True)
                if outcome:
                    value = 3 if outcome.winner is not None else 0
                    distance = 0
                else:
                    wdl = -self.tables.probe_wdl(board)
                    dtz = abs(self.tables.probe_dtz(board))
                    # Rounded DTZ near a fifty-move claim needs more information;
                    # use search if no certified winning alternative is available.
                    if abs(wdl) == 2 and board.halfmove_clock + dtz >= 99:
                        uncertain = True
                        continue
                    value = wdl if abs(wdl) == 2 else 0
                    distance = 1 if board.halfmove_clock == 0 else dtz + 1
                progress = -distance if value > 0 else distance if value < 0 else 0
                choices.append(((value, progress), move))
            except chess.syzygy.MissingTableError:
                return None
            finally:
                board.pop()
        if not choices:
            return None
        key, best = max(choices, key=lambda item: item[0])
        return best if not uncertain or key[0] > 0 else None
