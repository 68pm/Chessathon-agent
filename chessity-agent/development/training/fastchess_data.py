"""Audit the supplied fast-chess games and produce history-aware, teacher-verified targets."""

import argparse
import csv
import json
import time
from collections import Counter, defaultdict, deque
from pathlib import Path

import chess
import chess.pgn
import numpy as np

from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import SF
from training.chess_curriculum import describe
from training.puzzle_data import digest
from training.puzzle_verifier import Verifier, duplicate_key, root_key

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "runs/fastchess-pilot-20260906"
CONFIG = ROOT / "configs/fastchess-pilot.json"


def read_rows(path):
    with Path(path).open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def write_rows(path, rows):
    with Path(path).open("w", encoding="utf-8", newline="\n") as stream:
        for row in rows:
            stream.write(json.dumps(row, separators=(",", ":")) + "\n")


def restore(row):
    history = row["relevant_history"]
    board = chess.Board(history["start_fen"])
    for uci in history["moves"]:
        board.push_uci(uci)
    if board.fen() != row["solver_fen"]:
        raise ValueError("History does not reconstruct the labelled position")
    return board


def clock_regime(value):
    return "under_3s" if value < 3 else "under_10s" if value < 10 else "ordinary"


def clear_observation(row):
    """A generated child is not the parent's observed human move or clock record."""
    for name in ["played_move_uci", "played_move_san", "clock_before_estimate_seconds",
                 "clock_after_recorded_seconds", "opponent_clock_last_recorded_seconds",
                 "human_move_accepted", "observed_move_replaced_by_soft_alternatives",
                 "heldout_candidate_eligible", "cross_split_position_overlap", "recommended_move"]:
        row.pop(name, None)
    row.update(fen=row["solver_fen"], played_uci=None, clock_regime="unobserved_derived_position",
               label_kind="independently_verified_legal_branch", ply=chess.Board(row["solver_fen"]).ply() + 1)
    return row


def eco_family(eco):
    if "B10" <= eco <= "B19":
        return "caro_kann"
    if "C50" <= eco <= "C59":
        return "italian"
    if "D30" <= eco <= "D69":
        return "qgd"
    return "fallback"


def balanced(rows, maximum, seed, per_game=8):
    """Cycle factual strata; cap related examples without claiming population representativeness."""
    buckets = defaultdict(list)
    for row in rows:
        key = (row["player"], row["solver_colour"], row["primary_phase"],
               row["clock_regime"], row["player_result"], row["opening_family"])
        buckets[key].append(row)
    queues = [deque(sorted(group, key=lambda r: digest(f"{seed}:{r['id']}")))
              for _, group in sorted(buckets.items(), key=lambda item: digest(f"{seed}:{item[0]}"))]
    games, chosen = Counter(), []
    while queues and len(chosen) < maximum:
        next_queues = []
        for group in queues:
            while group and games[group[0]["family_id"]] >= per_game:
                group.popleft()
            if group and len(chosen) < maximum:
                row = group.popleft()
                chosen.append(row)
                games[row["family_id"]] += 1
            if group:
                next_queues.append(group)
        queues = next_queues
    return chosen


def prior_evidence():
    """Exclude previously seen boards from new evaluation, including colour mirrors."""
    any_keys, held_keys, games = set(), set(), set()
    samples = ROOT / "runs/magnus-mixed-20260906/mixture/samples.jsonl"
    for row in read_rows(samples):
        key = duplicate_key(chess.Board(row["fen"]))
        any_keys.add(key)
        if row["split"] != "train":
            held_keys.add(key)
        games.add(row["game_id"])
    value_path = ROOT / "runs/unattended-20260905-away/data-300000/dataset.npz"
    with np.load(value_path, allow_pickle=False) as values:
        for fen, split in zip(values["fen"], values["split"], strict=True):
            key = duplicate_key(chess.Board(str(fen)))
            any_keys.add(key)
            if int(split) != 0:
                held_keys.add(key)
    for row in read_rows(ROOT / "runs/puzzle-pilot-20260906/data/verified.jsonl"):
        key = duplicate_key(chess.Board(row["solver_fen"]))
        any_keys.add(key)
        if row["split"] != "train":
            held_keys.add(key)
    return any_keys, held_keys, games


def base_row(board, uid, split, history, **fields):
    return dict(id=uid, solver_fen=board.fen(), split=split,
                solver_colour="white" if board.turn else "black",
                relevant_history=dict(start_fen=chess.STARTING_FEN, moves=list(history), complete=True),
                draw_rule_context="Complete supplied PGN prefix replayed; claims checked by verifier.",
                dataset_version="hikaru-gotham-verified-pilot-v1", **fields)


def prepare(config, out):
    if out.exists():
        raise ValueError("Fresh preparation directory required")
    out.mkdir(parents=True)
    pack = ROOT / config["pack"]
    expected = json.loads((pack / "manifest.json").read_text())["summary"]
    imported = json.loads((pack / "import.json").read_text())
    assert all(sha256(pack / name) == info["sha256"] for name, info in imported["files"].items())
    metadata = {r["game_id"]: r for r in csv.DictReader((pack / "games.csv").open(encoding="utf-8"))}
    observations = read_rows(pack / "player-decisions.jsonl")
    by_game = defaultdict(dict)
    for row in observations:
        assert row["ply"] not in by_game[row["game_id"]]
        by_game[row["game_id"]][row["ply"]] = row
    assert len(metadata) == expected["games"] and len(observations) == expected["player_decisions"]
    checked, history, split_keys, game_seen = [], {}, defaultdict(set), set()
    source_counts = Counter()
    with (pack / "games.pgn").open(encoding="utf-8") as stream:
        while (game := chess.pgn.read_game(stream)) is not None:
            assert not game.errors
            url = game.headers.get("Link", game.headers["Site"])
            game_id = url.rstrip("/").split("/")[-1]
            assert game_id in metadata and game_id not in game_seen
            game_seen.add(game_id)
            meta = metadata[game_id]
            assert url == meta["source_url"] and game.headers["TimeControl"] == meta["time_control"]
            assert game.headers["Result"] == meta["result"]
            side = meta["player_colour"]
            assert game.headers[side.title()].lower() == meta["player"]
            board, moves = game.board(), []
            assert board.fen() == chess.STARTING_FEN
            source_counts[meta["player"]] += 1
            for ply, node in enumerate(game.mainline(), 1):
                move = node.move
                assert move in board.legal_moves
                if ("white" if board.turn else "black") == side:
                    raw = by_game[game_id][ply]
                    assert raw["fen"] == board.fen() and raw["played_move_uci"] == move.uci()
                    assert raw["played_move_san"] == board.san(move)
                    assert raw["player"] == meta["player"] and raw["player_colour"] == side
                    assert raw["provisional_split"] == meta["provisional_split"]
                    assert raw["game_result"] == meta["result"] and raw["time_control"] == meta["time_control"]
                    assert abs(node.clock() - raw["clock_after_recorded_seconds"]) < 0.002
                    key = duplicate_key(board)
                    split_keys[key].add(raw["provisional_split"])
                    checked.append(dict(raw, id=f"bundle:{game_id}:{ply}", canonical_key=key,
                                        family_id=f"chesscom:{game_id}", solver_fen=board.fen(),
                                        solver_colour=side, played_uci=move.uci(), split=raw["provisional_split"],
                                        source_url=url, source_game_id=game_id, source_eco=game.headers.get("ECO", ""),
                                        origin_type="supplied_player_game", player_result=meta["player_result"],
                                        clock_regime=clock_regime(raw["clock_before_estimate_seconds"]),
                                        opening_family=eco_family(game.headers.get("ECO", "")),
                                        primary_family="ordinary_negative_control", **describe(board, move)))
                moves.append(move.uci())
                board.push(move)
            assert len(moves) == int(meta["plies"])
            history[game_id] = moves
    assert len(checked) == len(observations) and game_seen == set(metadata)
    assert dict(source_counts) == expected["players"]
    print(f"Replayed {len(game_seen)} games and checked {len(checked)} decisions/clocks", flush=True)
    any_prior, held_prior, prior_games = prior_evidence()
    print(f"Loaded {len(any_prior)} prior exact/mirrored board exclusions", flush=True)
    excluded, seen, pools = Counter(), set(), defaultdict(list)
    for row in sorted(checked, key=lambda r: digest(r["id"])):
        key = row["canonical_key"]
        cause = ("cross_split_board" if len(split_keys[key]) > 1 else
                 "previous_source_game" if digest(row["source_url"]) in prior_games else
                 "previous_board" if key in any_prior else
                 "within_split_duplicate" if key in seen else None)
        if cause:
            excluded[cause] += 1
            continue
        seen.add(key)
        pools[row["split"]].append(row)
    candidates = []
    for split, target in config["human_verified_targets"].items():
        pool = balanced(pools[split], min(target * 4, 6400 if split == "train" else 768), config["seed"])
        for row in pool:
            row["relevant_history"] = dict(start_fen=chess.STARTING_FEN,
                                           moves=history[row["game_id"]][:row["ply"] - 1], complete=True)
            row["dataset_version"] = "hikaru-gotham-verified-pilot-v1"
            row["draw_rule_context"] = "Complete supplied PGN history; no inferred human think-time target."
        candidates.extend(pool)
        assert len(pool) >= target
    write_rows(out / "candidates.jsonl", candidates)
    # Graph positions can overlap prior training, but never prior held-out positions or new held-out boards.
    graph_forbidden = held_prior | {key for key, splits in split_keys.items() if splits != {"train"}}
    (out / "train-forbidden-keys.txt").write_text("\n".join(sorted(graph_forbidden)), encoding="utf-8")
    graph_pool, graph_seen = [], set()
    reference_count = 0
    with (pack / "opening-reference.tsv").open(encoding="utf-8") as stream:
        references = list(csv.DictReader(stream, delimiter="\t"))
    for ref in references:
        board, prefix = chess.Board(), []
        branch = eco_family(ref["eco"])
        for uci in ref["uci"].split():
            move = chess.Move.from_uci(uci)
            assert move in board.legal_moves
            role = "queens_gambit" if branch == "qgd" and board.turn else branch
            own = (board.turn and branch == "italian") or (not board.turn and branch in {"caro_kann", "qgd"}) or role == "queens_gambit"
            key = duplicate_key(board)
            # The first few common moves offer little evidence of understanding; retain them as references only.
            if own and len(prefix) >= 4 and key not in graph_forbidden and key not in graph_seen:
                graph_seen.add(key)
                graph_pool.append(base_row(board, "graph:" + digest(root_key(board)), "train", prefix,
                    family_id="reference:" + ref["eco"], source_game_id=None,
                    source_url="https://github.com/lichess-org/chess-openings", origin_type="opening_reference",
                    opening_family=role, branch_name=ref["name"], reference_eco=ref["eco"],
                    played_uci=uci, primary_family="opening_decision", **describe(board, move)))
            prefix.append(uci)
            board.push(move)
        assert board.fen() == ref["final_fen"]
        reference_count += 1
    assert reference_count == expected["opening_reference_lines"]
    # Actual train games add deviations, early middlegames and fallback families absent from the reference table.
    for row in sorted(checked, key=lambda r: digest("graph" + r["id"])):
        board = chess.Board(row["solver_fen"])
        role = "queens_gambit" if row["opening_family"] == "qgd" and board.turn else row["opening_family"]
        own = (board.turn and role in {"italian", "queens_gambit"}) or (not board.turn and role in {"caro_kann", "qgd"}) or role == "fallback"
        key = row["canonical_key"]
        if row["split"] != "train" or not 5 <= row["ply"] <= 44 or not own or key in graph_seen or key in graph_forbidden:
            continue
        # Do not move a source game from an old validation/test split into the new curriculum.
        if digest(row["source_url"]) in prior_games:
            continue
        graph_seen.add(key)
        graph_pool.append(dict(row, id="graph:" + digest(root_key(board)), opening_family=role,
                               branch_name=row["source_eco"], relevant_history=dict(start_fen=chess.STARTING_FEN,
                               moves=history[row["game_id"]][:row["ply"] - 1], complete=True)))
    write_rows(out / "graph-candidates.jsonl", graph_pool)
    save_json(out / "audit.json", {"pack": imported, "games_replayed": len(game_seen),
        "decisions_checked": len(checked), "recorded_clocks_checked": len(checked),
        "players": source_counts, "time_controls": dict(Counter(r["time_control"] for r in metadata.values())),
        "exact_target_clock_games": sum(r["time_control"] == "120+0.5" for r in metadata.values()),
        "legal_opening_lines": reference_count, "prior_board_keys": len(any_prior),
        "prior_game_ids": len(prior_games), "exclusions": excluded,
        "candidate_splits": dict(Counter(r["split"] for r in candidates)),
        "graph_candidates_by_family": dict(Counter(r["opening_family"] for r in graph_pool)),
        "remaining_limitations": "Whole supplied games and legal branches keep their provisional split. Exact/mirrored boards shared across splits or earlier datasets are removed from the fresh assessment pool. Opening graph is train-only and avoids earlier held-out boards. Original 300k value data lacks recoverable game IDs; related positions, familiar opening families and unknown teacher-data overlap cannot be completely excluded."})
    print(json.dumps(json.loads((out / "audit.json").read_text()), indent=2), flush=True)


def enrich(row):
    """Original curriculum notes are prompts to verify, never additional target rewards."""
    family = row.get("opening_family", "fallback")
    themes = {
        "italian": "Compare d3 preparation with c3/d4 expansion; check ...d5 and f7 tactics before spending tempi on a knight route.",
        "caro_kann": "Coordinate the light-squared bishop and king safety; compare ...c5/...f6 breaks only when the concrete line supports them.",
        "qgd": "Preserve central tension or release it with justified ...c5/...e5; watch the c-file, minority attack and isolated-pawn transitions.",
        "queens_gambit": "Compare central expansion with queenside play; first identify accepted, declined, Slav or Indian structures.",
        "fallback": "Develop and contest the centre while checking the opponent's actual threats; depart from the planned family when their moves require it.",
    }
    deep = row["candidate_moves"][-1]
    recommended = max(row["acceptable_first_moves"], key=lambda m: deep[m]["cp"] if deep[m]["cp"] is not None else 100000)
    row["recommended_move"] = recommended
    board = restore(row)
    context = describe(board, chess.Move.from_uci(recommended))
    row["primary_phase"] = context["primary_phase"]
    row["verified_move_context"] = {**context, "concept_tags": [tag.replace("played_", "recommended_") for tag in context["concept_tags"]]}
    if row["origin_type"] == "supplied_player_game":
        row["primary_family"] = ("mating_patterns" if row["confidence"] == "exact" else
                                 "defence" if board.is_check() else
                                 "endgame" if row["primary_phase"] == "endgame" else
                                 "ordinary_negative_control" if row["objective_type"] == "no_verified_tactical_win" else
                                 "quiet_ideas" if not board.is_capture(chess.Move.from_uci(recommended)) else "fundamental_tactics")
    row["concept_summary"] = themes[family]
    row["explanation_scope"] = "Original family-level study prompt, not a proved plan. The recorded concrete PV/alternatives support move quality only; no prose-matching reward."
    row["plan_failure_examples"] = row["tempting_bad_moves_and_refutations"][:3]
    row["task_tags"] = ["recall", "deviation", "plan", "refutation"]
    row["task_scope"] = "Root choices support recall; independently verified departures and continuation nodes are required for the other tasks."
    if row.get("played_uci"):
        played = row["played_uci"]
        row["human_move_accepted"] = played in row["acceptable_first_moves"]
        row["observed_move_replaced_by_soft_alternatives"] = not row["human_move_accepted"]
    return row


def verify(config, out):
    if (out / "manifest.json").exists():
        raise ValueError("Verified dataset is already frozen")
    assert sha256(SF) == "45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0"
    candidates = read_rows(out / "candidates.jsonl")
    candidates = [row for split in config["human_verified_targets"]
                  for row in balanced([r for r in candidates if r["split"] == split],
                                      len(candidates), config["seed"] + 11)]
    graphs = read_rows(out / "graph-candidates.jsonl")
    cache_path = out / "verification-cache.jsonl"
    cache = {r["id"]: r for r in read_rows(cache_path)} if cache_path.exists() else {}
    accepted, graph_nodes, errors, rejected = [], [], [], []
    counts, graph_counts, seen = Counter(), Counter(), set()
    all_split_keys = defaultdict(set)
    train_forbidden = set((out / "train-forbidden-keys.txt").read_text(encoding="utf-8").splitlines())
    for row in candidates:
        all_split_keys[duplicate_key(chess.Board(row["solver_fen"]))].add(row["split"])
    verifier = Verifier(SF, tuple(config["teacher_nodes"]))
    started = time.perf_counter()
    attempts = 0
    try:
        with cache_path.open("a", encoding="utf-8", newline="\n") as stream:
            def labelled(row):
                nonlocal attempts
                attempts += 1
                if attempts > config["max_verification_attempts"]:
                    raise RuntimeError("Verification pilot budget reached; preserve cache and inspect coverage")
                if row["id"] in cache:
                    item = cache[row["id"]]
                else:
                    result, reason = verifier.verify(row)
                    item = dict(id=row["id"], verified=result, reason=reason)
                    stream.write(json.dumps(item, separators=(",", ":")) + "\n")
                    stream.flush()
                if item["verified"] is None:
                    rejected.append(dict(id=row["id"], reason=item["reason"]))
                return item["verified"]

            for row in candidates:
                if counts[row["split"]] >= config["human_verified_targets"][row["split"]]:
                    continue
                if duplicate_key(chess.Board(row["solver_fen"])) in seen:
                    continue
                result = labelled(row)
                if result is None:
                    continue
                key = duplicate_key(chess.Board(row["solver_fen"]))
                assert key not in seen
                seen.add(key)
                accepted.append(enrich(result))
                counts[row["split"]] += 1
                if len(accepted) % 50 == 0:
                    print(f"Verified bundle {dict(counts)} after {attempts} attempts", flush=True)
                # Pair only a confirmed observed blunder with its independently verified punishment.
                bad = {b["move"] for b in result["tempting_bad_moves_and_refutations"]}
                if row["split"] == "train" and row["played_uci"] in bad and len(errors) < config["max_error_pairs"]:
                    board = restore(row)
                    board.push_uci(row["played_uci"])
                    child_key = duplicate_key(board)
                    if child_key in seen or child_key in train_forbidden or all_split_keys.get(child_key, {"train"}) != {"train"}:
                        continue
                    child = dict(row, id=row["id"] + ":punish", solver_fen=board.fen(),
                                 solver_colour="white" if board.turn else "black", played_uci=None,
                                 linked_parent_id=row["id"], primary_family="punish_blunder",
                                 origin_type="actual_observed_blunder_child",
                                 relevant_history={**row["relevant_history"], "moves": row["relevant_history"]["moves"] + [row["played_uci"]]})
                    clear_observation(child)
                    verified_child = labelled(child)
                    if verified_child:
                        seen.add(child_key)
                        errors.append(enrich(verified_child))
            assert dict(counts) == config["human_verified_targets"], dict(counts)
            # The graph is not an inference book. Verification may replace an unsound reference move.
            for row in graphs:
                family = row["opening_family"]
                if graph_counts[family] >= config["graph_nodes"][family]:
                    continue
                key = duplicate_key(chess.Board(row["solver_fen"]))
                if key in seen:
                    continue
                result = labelled(row)
                if result is None:
                    continue
                seen.add(key)
                graph_counts[family] += 1
                result = enrich(result)
                board = restore(row)
                result["node_key"] = root_key(board)
                result["history_is_separate_from_transposition_key"] = True
                board.push_uci(result["recommended_move"])
                reply_row = dict(row, id=row["id"] + ":reply", solver_fen=board.fen(), played_uci=None,
                                 solver_colour="white" if board.turn else "black",
                                 relevant_history={**row["relevant_history"], "moves": row["relevant_history"]["moves"] + [result["recommended_move"]]})
                clear_observation(reply_row)
                reply = labelled(reply_row) if not board.is_game_over(claim_draw=True) else None
                result["opponent_reply_verification"] = reply
                result["opponent_reply_status"] = "two_budget_verified" if reply else "terminal_or_unresolved"
                # Extend meaningful own-side decisions through sound replies, with full history.
                # This supplies depth when the small human sample/reference table lacks a branch.
                if reply and len(row["relevant_history"]["moves"]) < 56:
                    deep = reply["candidate_moves"][-1]
                    responses = sorted(reply["acceptable_first_moves"], key=lambda m: (-(deep[m]["cp"] or 0), m))[:2]
                    for response in responses:
                        board.push_uci(response)
                        child_key = duplicate_key(board)
                        if child_key not in train_forbidden and child_key not in seen and not board.is_game_over(claim_draw=True):
                            child = dict(row, id="graph:" + digest(root_key(board)), solver_fen=board.fen(),
                                         played_uci=None, origin_type="verified_opening_continuation",
                                         linked_parent_id=row["id"], continuation_reply=response,
                                         relevant_history={**row["relevant_history"], "moves": reply_row["relevant_history"]["moves"] + [response]})
                            clear_observation(child)
                            graphs.append(child)
                        board.pop()
                graph_nodes.append(result)
                if len(graph_nodes) % 25 == 0:
                    print(f"Verified graph {dict(graph_counts)}", flush=True)
            assert dict(graph_counts) == config["graph_nodes"], dict(graph_counts)
    finally:
        verifier.close()
    rows = accepted + errors + graph_nodes
    for row in rows:
        restore(row)
        for analysis in row["candidate_moves"]:
            for uci, info in analysis.items():
                board = restore(row)
                assert info["pv"][0] == uci
                for move in info["pv"]:
                    board.push_uci(move)
    keys, groups = defaultdict(set), defaultdict(set)
    for row in rows:
        keys[duplicate_key(chess.Board(row["solver_fen"]))].add(row["split"])
        groups[row["family_id"]].add(row["split"])
    assert all(len(s) == 1 for s in keys.values()) and all(len(s) == 1 for s in groups.values())
    write_rows(out / "verified.jsonl", rows)
    write_rows(out / "opening-graph.jsonl", graph_nodes)
    save_json(out / "rejections.json", rejected)
    report = dict(config=config, config_sha256=sha256(CONFIG), verified_sha256=sha256(out / "verified.jsonl"),
                  graph_sha256=sha256(out / "opening-graph.jsonl"), source_audit_sha256=sha256(out / "audit.json"),
                  human_positions=dict(counts), graph_nodes=dict(graph_counts), error_pairs=len(errors),
                  total_positions=len(rows), splits=dict(Counter(r["split"] for r in rows)),
                  phases=dict(Counter(r.get("primary_phase") for r in rows)),
                  confidence=dict(Counter(r["confidence"] for r in rows)),
                  observed_human_moves_accepted=sum(r["human_move_accepted"] for r in accepted),
                  observed_human_moves_replaced=sum(not r["human_move_accepted"] for r in accepted),
                  teacher_sha256=sha256(SF), seconds=time.perf_counter() - started,
                  attempts=attempts, quarantined=len(rejected), cross_split_duplicate_boards=0,
                  cross_split_families=0, all_legal_analysis_pvs_replayed=True,
                  scope="Two-budget approximate engine labels except exhaustively verified short mates. No teacher lookup ships; no human timing or puzzle reward is fitted into the game-value network.")
    save_json(out / "manifest.json", report)
    print(json.dumps(report, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["prepare", "verify"], required=True)
    args = parser.parse_args()
    config = json.loads(CONFIG.read_text())
    (prepare if args.stage == "prepare" else verify)(config, RUN / "data")


if __name__ == "__main__":
    main()
