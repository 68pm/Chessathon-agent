"""Replay source solutions and analysis lines, then independently repeat exact labels."""

import argparse
import json
from pathlib import Path

import chess

from scripts.alien_rating_ladder import save_json, sha256
from training.puzzle_data import decode_puzzle
from training.puzzle_verifier import duplicate_key, mate_moves


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.data / "manifest.json").read_text())
    assert manifest["sha256"] == sha256(args.data / "verified.jsonl")
    rows = [json.loads(s) for s in (args.data / "verified.jsonl").read_text().splitlines()]
    assert 200 <= len(rows) <= 500
    seen, families, exact_count, line_count = set(), {}, 0, 0
    for row in rows:
        board = chess.Board(row["solver_fen"])
        assert board.is_valid() and not board.is_game_over()
        key = duplicate_key(board)
        assert key not in seen
        seen.add(key)
        families.setdefault(row["family_id"], set()).add(row["split"])
        legal = {m.uci() for m in board.legal_moves}
        assert set(row["target_distribution"]) == legal
        assert abs(sum(row["target_distribution"].values()) - 1) < 1e-6
        assert set(row["acceptable_first_moves"]) <= legal
        if "original_record" in row:
            decoded = decode_puzzle(row["original_record"])
            assert decoded["solver_fen"] == row["solver_fen"]
        history = row["relevant_history"]
        if history["complete"]:
            restored = chess.Board(history["start_fen"])
            for uci in history["moves"]:
                restored.push_uci(uci)
            assert restored.fen() == board.fen()
            board = restored
        for analysis in row["candidate_moves"]:
            assert set(analysis) == legal
            for move, record in analysis.items():
                replay = board.copy()
                assert record["pv"][0] == move
                for uci in record["pv"]:
                    replay.push_uci(uci)
                line_count += 1
        if row["confidence"] == "exact":
            expected, _ = mate_moves(board, row["verification_budget"]["mate_horizon_plies"])
            assert expected == row["acceptable_first_moves"]
            exact_count += 1
    assert all(len(splits) == 1 for splits in families.values())
    report = {"verified_positions": len(rows), "legal_analysis_lines_replayed": line_count,
              "exact_mate_proofs_repeated": exact_count, "family_split_overlap": 0,
              "canonical_or_colour_mirror_duplicates": 0, "dataset_sha256": manifest["sha256"]}
    save_json(args.data / "audit.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
