"""Post-test sampled move-quality diagnosis; never feeds held-out losses into training."""

import json
from collections import Counter

import chess

from scripts.alien_rating_ladder import save_json
from scripts.magnus_benchmark import SF
from scripts.puzzle_evaluate import judge
from training.fastchess_data import CONFIG, RUN
from training.puzzle_data import digest
from training.puzzle_verifier import Verifier


def main():
    config = json.loads(CONFIG.read_text())
    out = RUN / "loss-audit.json"
    if out.exists():
        raise ValueError("Preserve existing post-test diagnosis")
    sources, examples = [], []
    for stage in ["comparison", "rated"]:
        report = json.loads((RUN / stage / "results.json").read_text())
        assert report["status"] == "complete"
        for game in report["games"]:
            if game["score"] != 0:
                continue
            sources.append(dict(stage=stage, id=game["id"], termination=game["termination"],
                                failed_colour=game["failed_colour"]))
            indices = [i for i, row in enumerate(game["moves"]) if row["white"] == game["candidate_white"]]
            selected = sorted({indices[min(len(indices) - 1, 8)], indices[len(indices) // 2],
                               indices[max(0, len(indices) - 5)]}) if indices else []
            board = chess.Board()
            for uci in game["opening"]:
                board.push_uci(uci)
            start = board.fen()
            for index in selected:
                row = game["moves"][index]
                examples.append(dict(id=f"post-test:{stage}:{game['id']}:{index}", stage=stage,
                    source_game_id=f"{stage}:{game['id']}", family_id=f"post-test:{stage}:{game['id']}",
                    split="test", solver_fen=row["fen"], played_uci=row["uci"],
                    primary_family="post_test_diagnosis", clock_before_ms=row["clock_before_ms"],
                    relevant_history=dict(start_fen=start, moves=[m["uci"] for m in game["moves"][:index]], complete=True)))
    examples = sorted(examples, key=lambda r: digest(r["id"]))[:48]
    verifier = Verifier(SF, tuple(config["teacher_nodes"]))
    rows, unresolved = [], []
    try:
        for row in examples:
            verified, reason = verifier.verify(row)
            if verified:
                rows.append(dict(id=row["id"], source_game_id=row["source_game_id"],
                                 clock_before_ms=row["clock_before_ms"], assessment=judge(verified, row["played_uci"]),
                                 verification=verified))
            else:
                unresolved.append(dict(id=row["id"], reason=reason))
            save_json(out, dict(status="running", rows=rows, unresolved=unresolved))
    finally:
        verifier.close()
    report = dict(status="complete", lost_games=sources, attempted_positions=len(examples), rows=rows,
                  unresolved=unresolved, known_loss_terminations=dict(Counter(r["termination"] for r in sources)),
                  sampled_verified_blunders=sum(r["assessment"].get("blunder") is True for r in rows),
                  scope="Sampled errors from completed test losses only; not a complete blunder census or causal decomposition of network versus search failures. Mate-scored/unstable positions may be unresolved, never counted as zero error. No test position enters training/replay.")
    save_json(out, report)
    print(json.dumps({k: v for k, v in report.items() if k not in {"rows", "lost_games", "unresolved"}}, indent=2), flush=True)


if __name__ == "__main__":
    main()
