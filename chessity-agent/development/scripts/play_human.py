"""Local terminal play with explicit engine and attacking-opening options."""

import argparse
import os

import chess

from engine.evaluation import Evaluator
from engine.openings import alien_move
from engine.search import Search


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--engine-color", choices=["white", "black"], default="black")
    p.add_argument("--style", choices=["none", "alien", "alien-selective"], default="none")
    p.add_argument(
        "--mode", choices=["classical", "neural", "hybrid", "phase"], default="classical"
    )
    p.add_argument("--model", default="models/value.npz")
    p.add_argument("--player-policy")
    p.add_argument("--policy-cp", type=int, default=20)
    p.add_argument("--alien-cp", type=int, default=15)
    p.add_argument("--seconds", type=float, default=1)
    p.add_argument("--fen", default=chess.STARTING_FEN)
    a = p.parse_args()
    if not 0 < a.seconds <= 60:
        p.error("Choose a move budget between 0 and 60 seconds")
    model = None
    if a.mode != "classical":
        for variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
            os.environ[variable] = "1"
        from engine.neural import NeuralValue

        model = NeuralValue(a.model)
    board = chess.Board(a.fen)
    policy = None
    if a.player_policy:
        for variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
            os.environ[variable] = "1"
        from engine.player_policy import PlayerPolicy

        policy = PlayerPolicy(a.player_policy)
    engine = Search(Evaluator(a.mode, model), player_policy=policy, policy_cp=a.policy_cp)
    own_color = chess.WHITE if a.engine_color == "white" else chess.BLACK
    print(f"Engine plays {a.engine_color}; mode={a.mode}; opening style={a.style}.")
    print("Enter a move such as e4 or e2e4; quit to stop.")
    if policy:
        print(f"Player-trained move preferences enabled ({engine.policy_cp}-centipawn bonus cap).")
    if a.style == "alien":
        print("Alien is experimental: a prepared knight sacrifice, then normal search.")
    elif a.style == "alien-selective":
        print(
            "Alien moves are optional search preferences; unfavourable sacrifices can be declined."
        )
    while not board.is_game_over(claim_draw=True):
        print("\n" + str(board) + "\n")
        if board.turn != own_color:
            try:
                text = input("Your move: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nGame closed.")
                return
            if text.lower() in {"quit", "exit"}:
                return
            try:
                move = board.parse_san(text)
            except ValueError:
                print("That move is not legal. Try again.")
                continue
        else:
            book = alien_move(board) if a.style in {"alien", "alien-selective"} else None
            forced = book if a.style == "alien" else None
            move = (
                forced
                or engine.run(
                    board,
                    a.seconds,
                    preferred_move=book if a.style == "alien-selective" else None,
                    preference_cp=a.alien_cp,
                ).move
            )
            print("Engine:", board.san(move), "(Alien opening)" if move == book else "")
        board.push(move)
    print(board.result(claim_draw=True))


if __name__ == "__main__":
    main()
