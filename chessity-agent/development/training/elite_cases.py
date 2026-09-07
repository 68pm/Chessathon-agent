"""Reconstruct the supplied elite cases and produce bounded, unbounded-score teacher labels."""

import argparse
import json
import re
from pathlib import Path

import chess
import chess.engine

from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import SF
from training.fastchess_data import ROOT, read_rows
from training.puzzle_verifier import Verifier

CONFIG = ROOT / "configs/elite-case-pilot.json"
RUN = ROOT / "runs/elite-case-pilot-20260907"


def completed_iteration(updates, legal, side):
    """Ignore bounded/stale snapshots and select a fully completed common depth."""
    depths = {}
    maximum_nodes = 0
    for info in updates:
        maximum_nodes = max(maximum_nodes, info.get("nodes", 0))
        if (not info.get("pv") or "score" not in info or "depth" not in info
                or info.get("lowerbound") or info.get("upperbound")):
            continue
        pv = [move.uci() for move in info["pv"]]
        if pv[0] not in legal:
            raise ValueError("Teacher emitted an illegal root")
        score = info["score"].pov(side)
        depths.setdefault(info["depth"], {})[info.get("multipv", 1)] = dict(
            cp=score.score(), mate=score.mate(), pv=pv, depth=info["depth"],
            nodes=info.get("nodes", 0), seconds=info.get("time", 0))
    for depth in sorted(depths, reverse=True):
        records = depths[depth]
        if set(records) == set(range(1, len(legal) + 1)) and {r["pv"][0] for r in records.values()} == legal:
            return {r["pv"][0]: dict(r, total_search_nodes_observed=maximum_nodes) for r in records.values()}
    raise ValueError("Teacher did not finish an unbounded-score full-legal common-depth iteration")


class EliteVerifier(Verifier):
    def analyse(self, board, nodes):
        self.engine.configure({"Clear Hash": None})
        legal = {move.uci() for move in board.legal_moves}
        with self.engine.analysis(board, chess.engine.Limit(nodes=nodes), multipv=len(legal), game=object()) as stream:
            return completed_iteration(stream, legal, board.turn)


def extract_cases(document):
    rows = {}
    entries = 0
    for section in re.split(r"(?m)^## ", document):
        fen = re.search(r"```text\s*\n([^\n]+)\n```", section)
        identity = re.search(r"(?:\*\*Position ID:\*\*|Position)\s*`([^`]+)`", section)
        played = re.search(r"\*\*(?:Played|Observed decision):\*\*\s*`?([^`\n]+)", section)
        if not (fen and identity and played):
            continue
        board = chess.Board(fen.group(1).strip())
        assert board.is_valid()
        san = re.sub(r"^\d+\.{1,3}", "", played.group(1).strip()).split(".")[0].strip()
        move = board.parse_san(san)
        uid = identity.group(1)
        row = dict(id="elite-case:" + uid, source_position_id=uid, solver_fen=board.fen(),
                   played_uci=move.uci(), source_game_id=uid.split(":")[0], split="train",
                   family_id="elite-game:" + uid.split(":")[0], primary_family="elite_case",
                   relevant_history=dict(complete=False, reason="Supplied case FEN; full preceding PGN unavailable."),
                   source_title=section.splitlines()[0], origin_type="supplied_elite_case",
                   label_status="observed_move_requiring_independent_teacher_verification")
        if uid in rows:
            assert all(row[k] == rows[uid][k] for k in ["solver_fen", "played_uci"])
        else:
            rows[uid] = row
        entries += 1
    return list(rows.values()), entries


def verify_cached(rows, out):
    config = json.loads(CONFIG.read_text())
    out.mkdir(parents=True, exist_ok=True)
    context = dict(config_sha256=sha256(CONFIG), teacher_sha256=sha256(SF),
                   verifier_sha256=sha256(Path(__file__)), base_verifier_sha256=sha256(ROOT / "training/puzzle_verifier.py"))
    context_path = out / "context.json"
    if context_path.exists():
        assert json.loads(context_path.read_text()) == context
    else:
        save_json(context_path, context)
    cache_path = out / "cache.jsonl"
    cache = {row["id"]: row for row in read_rows(cache_path)} if cache_path.exists() else {}
    verifier = EliteVerifier(SF, tuple(config["teacher_nodes"]))
    accepted, rejected = [], []
    try:
        for index, row in enumerate(rows):
            fingerprint = __import__("hashlib").sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()
            if row["id"] in cache:
                item = cache[row["id"]]
                assert item["row_sha256"] == fingerprint
            else:
                try:
                    verified, reason = verifier.verify(row)
                except ValueError as error:
                    verified, reason = None, str(error)
                if verified:
                    for analysis in verified["candidate_moves"]:
                        for answer in analysis.values():
                            board = chess.Board(row["solver_fen"])
                            for uci in answer["pv"]:
                                board.push_uci(uci)
                item = dict(id=row["id"], row_sha256=fingerprint, verified=verified, reason=reason)
                with cache_path.open("a", encoding="utf-8") as stream:
                    stream.write(json.dumps(item) + "\n")
                cache[row["id"]] = item
            (accepted if item["verified"] else rejected).append(item["verified"] or dict(id=row["id"], reason=item["reason"]))
            if (index + 1) % 16 == 0:
                print(f"reviewed {index+1}/{len(rows)}; {len(accepted)} verified", flush=True)
    finally:
        verifier.close()
    (out / "verified.jsonl").write_text("".join(json.dumps(row) + "\n" for row in accepted), encoding="utf-8")
    save_json(out / "rejections.json", rejected)
    save_json(out / "manifest.json", dict(status="complete", attempted=len(rows), accepted=len(accepted),
              quarantined=len(rejected), verified_sha256=sha256(out / "verified.jsonl"), context=context,
              scope="Finite 80k/320k full-legal teacher estimates using unbounded UCI score snapshots. Unknown source-case repetition history remains unavailable; no game-theoretic certainty inferred."))
    return accepted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text())
    source = ROOT / config["source_document"]
    assert sha256(source) == config["source_sha256"]
    rows, entries = extract_cases(source.read_text(encoding="utf-8"))
    assert entries == 22 and len(rows) == 21
    RUN.mkdir(exist_ok=True)
    save_json(RUN / "case-import.json", dict(entries=entries, unique_cases=len(rows),
              unique_games=len({r["source_game_id"] for r in rows}), source_sha256=sha256(source),
              full_corpus_available=False, all_cases_training_only=True, weights_changed=False))
    if args.verify:
        assert json.loads((ROOT / "runs/threephase-pilot-20260906/selection.json").read_text())["status"] == "complete"
        verified = verify_cached(rows, RUN / "cases")
        print(f"Verified {len(verified)}/{len(rows)} supplied cases", flush=True)


if __name__ == "__main__":
    main()
