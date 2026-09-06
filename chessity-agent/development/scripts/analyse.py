import argparse

import chess

from engine.evaluation import Evaluator
from engine.search import Search


def main():
    p = argparse.ArgumentParser(description="Analyse a chess position locally")
    p.add_argument("--fen", default=chess.STARTING_FEN)
    p.add_argument("--seconds", type=float, default=2)
    p.add_argument("--model", default="models/value.npz")
    p.add_argument("--style", choices=["none", "alien"], default="none")
    p.add_argument(
        "--mode", choices=["classical", "neural", "hybrid", "phase"], default="classical"
    )
    a = p.parse_args()
    model = None
    if a.mode != "classical":
        from engine.neural import NeuralValue

        model = NeuralValue(a.model)
    board = chess.Board(a.fen)
    if a.style == "alien":
        from engine.openings import alien_move

        move = alien_move(board)
        if move is not None:
            print(board)
            print("Experimental Alien opening preference:", board.san(move), move.uci())
            return
    result = Search(Evaluator(a.mode, model)).run(board, a.seconds)
    print(board)
    print(result)
    if result.move:
        print("Best move:", board.san(result.move), result.move.uci())


if __name__ == "__main__":
    main()
