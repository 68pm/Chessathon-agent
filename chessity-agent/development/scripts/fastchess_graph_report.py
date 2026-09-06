"""Add factual structures, sampled reply frequencies and study explanations to the offline graph."""

import csv
import json
from collections import Counter, defaultdict

import chess
import chess.pgn

from scripts.alien_rating_ladder import save_json, sha256
from training.fastchess_data import CONFIG, ROOT, RUN, read_rows, restore
from training.puzzle_verifier import root_key


def structure(board):
    isolated = {}
    for colour in [True, False]:
        pawns = board.pieces(chess.PAWN, colour)
        isolated["white" if colour else "black"] = [chess.square_name(p) for p in pawns
            if not any(abs(chess.square_file(other) - chess.square_file(p)) == 1 for other in pawns)]
    return dict(isolated_pawns=isolated,
                open_files=[chess.FILE_NAMES[i] for i, mask in enumerate(chess.BB_FILES)
                            if not mask & (board.pieces_mask(chess.PAWN, True) | board.pieces_mask(chess.PAWN, False))],
                queens_present=sum(len(board.pieces(chess.QUEEN, colour)) for colour in chess.COLORS),
                note="Mechanically checked current structure; no promise that a specific pawn break or endgame will be reached.")


def main():
    config = json.loads(CONFIG.read_text())
    pack = ROOT / config["pack"]
    graph = read_rows(RUN / "data/opening-graph.jsonl")
    wanted = set()
    for row in graph:
        board = restore(row)
        board.push_uci(row["recommended_move"])
        wanted.add(root_key(board))
    metadata = {r["game_id"]: r for r in csv.DictReader((pack / "games.csv").open(encoding="utf-8"))}
    frequencies = defaultdict(Counter)
    with (pack / "games.pgn").open(encoding="utf-8") as stream:
        while (game := chess.pgn.read_game(stream)) is not None:
            uid = game.headers["Link"].split("/")[-1]
            if metadata[uid]["provisional_split"] != "train":
                continue
            board = game.board()
            for move in game.mainline_moves():
                key = root_key(board)
                if key in wanted:
                    frequencies[key][move.uci()] += 1
                board.push(move)
                if board.ply() >= 80:
                    break
    lookup = {row["node_key"]: row["id"] for row in graph}
    for row in graph:
        board = restore(row)
        row["structure_facts"] = structure(board)
        move = chess.Move.from_uci(row["recommended_move"])
        row["recommended_san"] = board.san(move)
        row["move_effects"] = dict(capture=board.is_capture(move), check=board.gives_check(move),
                                   castling=board.is_castling(move), piece=chess.piece_name(board.piece_type_at(move.from_square)))
        board.push(move)
        observed = frequencies[root_key(board)]
        reply = row.get("opponent_reply_verification")
        row["opponent_observed_training_replies"] = dict(observed)
        row["reply_frequency_scope"] = "Only supplied training games; zero/one observation means rare in this small sample, not rare in chess generally."
        row["strong_rare_replies_in_sample"] = [m for m in reply["acceptable_first_moves"] if observed[m] <= 1] if reply else []
        row["edges_after_sound_replies"] = []
        for response in reply["acceptable_first_moves"] if reply else []:
            board.push_uci(response)
            row["edges_after_sound_replies"].append(dict(reply=response, resulting_node_key=root_key(board),
                                                        own_decision_node=lookup.get(root_key(board))))
            board.pop()
    save_json(RUN / "data/opening-knowledge-graph.json", {
        "training_only": True, "ships_in_runtime": False, "label_graph_sha256": sha256(RUN / "data/opening-graph.jsonl"),
        "nodes": graph, "counts": dict(Counter(r["opening_family"] for r in graph)),
        "coverage_limit": "A pilot of selected decisions and verified replies, not a complete connected repertoire. Search handles uncovered branches. Family notes are study hypotheses; the concrete engine alternatives support move-quality estimates only."})
    lines = ["# Fast-chess opening pilot", "", "The graph is an offline training curriculum. It is not included in the competition agent and its training-board recall is reported separately from held-out play.", "",
             "| Family | Verified own-side nodes |", "|---|---:|"]
    for family, count in sorted(Counter(r["opening_family"] for r in graph).items()):
        lines.append(f"| {family} | {count} |")
    lines += ["", "Every root decision has full legal alternatives at 80k and 320k Stockfish nodes, explicit mover-relative scores, uncertainty and PGN/reference provenance. Where opponent-reply verification remains unresolved it is marked as such. The graph merges actual transpositions by state and keeps history separately. It is a small selection of decisions; uncovered openings still require normal search.", "",
              "These are original study prompts and mechanically checked board facts. General plans are not rewards and do not establish positional understanding. Teacher-labelled lookup data remains outside the runtime ZIP.", "", "## Selected training examples", ""]
    selected = [row for family in config["graph_nodes"] for row in [r for r in graph if r["opening_family"] == family][:4]]
    for row in selected:
        board = restore(row)
        pv = row["candidate_moves"][-1][row["recommended_move"]]["pv"]
        san = []
        for uci in pv[:8]:
            move = chess.Move.from_uci(uci)
            san.append(board.san(move))
            board.push(move)
        lines += [f"### {row['opening_family']}: {row['id']}", "", f"FEN: `{row['solver_fen']}`", "",
                  f"Supported move: **{row['recommended_san']}**. Sound alternatives: `{', '.join(row['acceptable_first_moves'])}`. Concrete continuation estimate: {' '.join(san)}.", "",
                  row["concept_summary"], "", f"Current structure: `{json.dumps(row['structure_facts'])}`.", "",
                  f"Sample-rare strong replies: `{', '.join(row['strong_rare_replies_in_sample']) or 'none established'}`. See the graph for full verification and sampled frequencies.", ""]
    (ROOT / "docs/FASTCHESS_OPENING_GRAPH.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(json.dumps({"nodes": len(graph), "report": "docs/FASTCHESS_OPENING_GRAPH.md"}), flush=True)


if __name__ == "__main__":
    main()
