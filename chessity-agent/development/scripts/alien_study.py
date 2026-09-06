"""Independent analysis of generated opening positions using an offline teacher."""

import argparse
import json
import os
import subprocess
from pathlib import Path

import chess
import chess.engine

from engine.openings import ALIEN_LINE
from engine.search import Search


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--engine", type=Path, required=True)
    p.add_argument("--nodes", type=int, default=300000)
    p.add_argument("--out", type=Path, default=Path("runs/alien-study.json"))
    a = p.parse_args()
    positions = []
    b = chess.Board()
    for san in ALIEN_LINE:
        if san in ["Nxf7", "Nf3"]:
            positions.append(("before_" + san, b.copy(), san))
        b.push_san(san)
    positions.append(("after_7_Nf3", b.copy(), None))
    for defense in ["e6", "Nbd7", "Ke8", "Bg4"]:
        c = b.copy()
        c.push_san(defense)
        positions.append(("after_7_" + defense, c, "Ne5+" if defense == "Bg4" else None))
    rows = []
    with chess.engine.SimpleEngine.popen_uci(
        str(a.engine), creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    ) as teacher:
        teacher.configure({"Threads": 1, "Hash": 64, "UCI_LimitStrength": False})
        for name, board, selected in positions:
            info = teacher.analyse(board, chess.engine.Limit(nodes=a.nodes), game=object())
            row = {
                "name": name,
                "fen": board.fen(),
                "best_uci": info["pv"][0].uci(),
                "best_san": board.san(info["pv"][0]),
                "white_cp": info["score"].white().score(mate_score=10000),
                "depth": info.get("depth"),
                "pv_uci": [m.uci() for m in info["pv"]],
                "nodes": info.get("nodes"),
            }
            if selected:
                move = board.parse_san(selected)
                forced = teacher.analyse(
                    board, chess.engine.Limit(nodes=a.nodes), root_moves=[move], game=object()
                )
                row.update(
                    {
                        "selected_san": selected,
                        "selected_white_cp": forced["score"].white().score(mate_score=10000),
                        "selected_depth": forced.get("depth"),
                    }
                )
            own = Search().run(board, 0.5)
            row.update(
                {
                    "own_classical_san": board.san(own.move),
                    "own_depth": own.depth,
                    "own_score_mover_cp": own.score,
                }
            )
            rows.append(row)
            print(json.dumps(row), flush=True)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(
        json.dumps(
            {
                "provenance": "Independently constructed legal positions from the public opening sequence; no player game history. Stockfish 19 used offline for analysis only, no weights or code copied into the agent.",
                "sequence_san": ALIEN_LINE,
                "nodes_per_search": a.nodes,
                "limitations": "Finite-depth teacher evaluations, not proof. Scores are White perspective; no human win-rate inference. This is opening preparation, not neural training or player-style cloning.",
                "positions": rows,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
