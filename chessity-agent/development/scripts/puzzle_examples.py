"""Readable verified training examples, with explicit proof and analysis limits."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import chess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    groups = defaultdict(list)
    for line in (args.data / "verified.jsonl").read_text().splitlines():
        row = json.loads(line)
        if row["split"] == "train":
            groups[row["primary_family"]].append(row)
    examples = []
    for i in range(max(map(len, groups.values()))):
        for group in groups.values():
            if i < len(group):
                examples.append(group[i])
        if len(examples) >= 30:
            break
    examples = examples[:30]
    assert len(examples) == 30
    text = ["# Thirty verified examples from the training split", "",
            "These examples show actual labels used in the pilot. Source motif tags describe sampling categories; they are not independently proved explanations. Only exhaustive short mates are exact. Other targets are estimates from Stockfish 19 at two fixed budgets. Principal variations illustrate one continuation and do not prove coverage of every defensive reply. No held-out test examples appear here.", ""]
    for index, row in enumerate(examples, 1):
        board = chess.Board(row["solver_fen"])
        text += [f"## {index}. {row['primary_family']}: {row['id']}", "",
                 f"{row['solver_colour'].capitalize()} to move. Origin: `{row['origin_type']}`. Confidence: **{row['confidence']}**.", "",
                 f"Objective: {row['objective_predicate']}", "", "```text", str(board), "  a b c d e f g h", "```", "",
                 f"FEN: `{row['solver_fen']}`", "",
                 "Accepted alternatives: " + ", ".join(f"{board.san(chess.Move.from_uci(m))} (`{m}`)" for m in row["acceptable_first_moves"]) + ".", "",
                 "Source tags: " + ", ".join(row["secondary_themes"]) + ".", "",
                 f"Proof type: `{row['proof_type']}`. Verification: `{json.dumps(row['verification_budget'])}`.", ""]
        for line in row["continuation_branches"][:2]:
            copy = board.copy()
            san = []
            for uci in line[:10]:
                move = chess.Move.from_uci(uci)
                san.append(copy.san(move))
                copy.push(move)
            text += ["Illustrative continuation: " + " ".join(san) + ".", ""]
        mistakes = row["tempting_bad_moves_and_refutations"][:2]
        for mistake in mistakes:
            text += [f"Verified bad alternative `{mistake['move']}`: estimated regret {mistake['regret_cp']}cp at the two budgets; illustrative refutation `{ ' '.join(mistake['refutation'][:10]) }`.", ""]
        if not mistakes:
            text += ["No separate stable 200cp mistake label was assigned to this record. A failed short-mate objective is not automatically a proved lost game.", ""]
        if row.get("source_url"):
            text += [f"Source reference: `{row['source_url']}`. Family: `{row['family_id']}`.", ""]
    args.out.write_text("\n".join(text), encoding="utf-8", newline="\n")


if __name__ == "__main__":
    main()
