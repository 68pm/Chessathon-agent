"""History-aware, event-grouped three-phase diagnostic data; no implicit weight training."""

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict

import chess
import chess.pgn

from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import SF
from scripts.threephase_matches import CONFIG, RUN
from training.fastchess_data import ROOT, prior_evidence, read_rows, write_rows
from training.puzzle_data import digest
from training.puzzle_verifier import Verifier, duplicate_key

PACK = ROOT / "data/three-phase-pack"
PHASES = ["opening", "middlegame", "transition", "endgame"]


def normalized(value):
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def prepare():
    config = json.loads(CONFIG.read_text())
    out = RUN / "data"
    if out.exists():
        raise ValueError("Preserve existing preparation")
    out.mkdir(parents=True)
    supplied_cases = read_rows(PACK / "engine-cases.jsonl")
    public_case_games = {r["game_id"] for r in supplied_cases}
    indices = {r["game_id"]: r for r in read_rows(PACK / "game-index.jsonl")}
    games = {}
    with (PACK / "grandmaster-games.pgn").open(encoding="utf-8") as stream:
        while (game := chess.pgn.read_game(stream)) is not None:
            assert not game.errors
            uid = game.headers["CorpusId"]
            games[uid] = dict(start_fen=game.board().fen(), moves=[m.uci() for m in game.mainline_moves()])
    assert set(games) == set(indices)
    parent = {uid: uid for uid in games}

    def find(uid):
        while parent[uid] != uid:
            parent[uid] = parent[parent[uid]]
            uid = parent[uid]
        return uid

    def union(a, b):
        a, b = find(a), find(b)
        if a != b:
            parent[max(a, b)] = min(a, b)

    event_seen, prefix_seen, full_seen = {}, {}, {}
    event_keys, prefix_keys = {}, {}
    for uid, game in games.items():
        headers = indices[uid]["headers"]
        event, site, year = normalized(headers.get("Event", "")), normalized(headers.get("Site", "")), headers.get("Date", "")[:4]
        # Generic online/unknown event names do not mean every game is one event.
        if event not in {"", "live chess", "rated blitz game", "rated bullet game", "casual game"} and site and year.isdigit():
            event_key = (event, site, year)
            event_keys[uid] = str(event_key)
            if event_key in event_seen:
                union(uid, event_seen[event_key])
            event_seen[event_key] = uid
        if len(game["moves"]) >= 32:
            prefix = " ".join(game["moves"][:32])
            prefix_keys[uid] = prefix
            if prefix in prefix_seen:
                union(uid, prefix_seen[prefix])
            prefix_seen[prefix] = uid
        full = game["start_fen"] + " " + " ".join(game["moves"])
        if full in full_seen:
            union(uid, full_seen[full])
        full_seen[full] = uid
    clusters = defaultdict(list)
    for uid in games:
        clusters[find(uid)].append(uid)
    split_by_game = {}
    for cluster, members in clusters.items():
        value = int(digest(f"{config['seed']}:{cluster}")[:8], 16) % 100
        split = "train" if value < 80 else "validation" if value < 90 else "test"
        if public_case_games.intersection(members):
            split = "train"
        for uid in members:
            split_by_game[uid] = split
    prior_keys, _, old_game_ids = prior_evidence()
    prior_extra_fens = set()

    def collect_fens(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key in {"fen", "solver_fen", "final_fen"} and isinstance(item, str):
                    prior_extra_fens.add(item)
                elif isinstance(item, (dict, list)):
                    collect_fens(item)
        elif isinstance(value, list):
            for item in value:
                collect_fens(item)

    for row in read_rows(ROOT / "runs/fastchess-pilot-20260906/data/verified.jsonl"):
        prior_extra_fens.add(row["solver_fen"])
    for path in (ROOT / "docs/evidence").glob("*.json"):
        if not path.name.startswith("threephase"):
            collect_fens(json.loads(path.read_text(encoding="utf-8")))
    prior_keys.update(duplicate_key(chess.Board(fen)) for fen in prior_extra_fens)
    previous_games = set()
    for uid, meta in indices.items():
        headers = meta["headers"]
        identity = headers.get("Link")
        if identity and hashlib.sha256(identity.encode()).hexdigest() in old_game_ids:
            previous_games.add(uid)
    supplied_collisions = set((PACK / "cross-split-board-keys.txt").read_text().splitlines())
    raw, cross, excluded = [], defaultdict(set), Counter()
    for phase in PHASES:
        for row in read_rows(PACK / f"{phase}-positions.jsonl"):
            uid = row["game_id"]
            if row["board_key"] in supplied_collisions:
                excluded["supplied_cross_split_board"] += 1
                continue
            if uid in previous_games:
                excluded["recognized_previous_source_game"] += 1
                continue
            board = chess.Board(row["fen"])
            key = duplicate_key(board)
            if key in prior_keys:
                excluded["previously_exposed_exact_or_mirrored_board"] += 1
                continue
            if row["ply"] <= 12:
                excluded["early_opening_prefix_policy"] += 1
                continue
            row["split"] = split_by_game[uid]
            row["canonical_key"] = key
            cross[key].add(row["split"])
            raw.append(row)
    forbidden = {key for key, splits in cross.items() if len(splits) > 1}
    eligible = defaultdict(list)
    seen = set()
    for row in sorted(raw, key=lambda r: digest(f"{config['seed']}:{r['position_id']}")):
        if row["canonical_key"] in forbidden:
            excluded["regrouped_cross_split_exact_or_mirror"] += 1
            continue
        if row["canonical_key"] in seen:
            excluded["within_split_duplicate"] += 1
            continue
        seen.add(row["canonical_key"])
        eligible[row["split"], row["phase"]].append(row)
    candidates, chosen_counts, player_counts = [], Counter(), Counter()
    for (split, phase), group in sorted(eligible.items()):
        buckets = defaultdict(list)
        for row in group:
            headers = indices[row["game_id"]]["headers"]
            buckets[row["player"], row["colour"], row["result"], headers.get("ECO", "unknown")[:1]].append(row)
        queues = list(buckets.values())
        per_game = Counter()
        target = config["phase_diagnostic_targets"][split] // len(PHASES) * 5
        selected = []
        while queues and len(selected) < target:
            remaining = []
            for queue in queues:
                while queue and per_game[queue[-1]["game_id"]] >= 8:
                    queue.pop()
                if queue and len(selected) < target:
                    row = queue.pop()
                    per_game[row["game_id"]] += 1
                    selected.append(row)
                if queue:
                    remaining.append(queue)
            queues = remaining
        for row in selected:
            uid, ply = row["game_id"], row["ply"]
            game, headers = games[uid], indices[uid]["headers"]
            history = dict(start_fen=game["start_fen"], moves=game["moves"][:ply - 1], complete=True)
            board = chess.Board(history["start_fen"])
            for move in history["moves"]:
                board.push_uci(move)
            assert board.fen() == row["fen"] and game["moves"][ply - 1] == row["played_uci"]
            enriched = dict(id=f"threephase:{row['position_id']}", solver_fen=row["fen"], split=split,
                canonical_key=row["canonical_key"], source_game_id=uid, family_id=find(uid),
                primary_family=f"threephase_{phase}", primary_phase=phase, source_phase_heuristic="pack-v1",
                relevant_history=history, solver_colour=row["colour"], played_uci=row["played_uci"],
                player=row["player"], recorded_game_result=row["result"], source_headers=headers,
                provenance=indices[uid]["sources"], source_event_group=event_keys.get(uid),
                clock_after_recorded_seconds=row["clock_after_seconds"],
                observed_elo=headers.get(row["colour"].title() + "Elo"), time_control=headers.get("TimeControl"),
                source_label_status="observed_move_not_verified_best", dataset_version="threephase-diagnostic-v1")
            candidates.append(enriched)
            chosen_counts[f"{split}:{phase}"] += 1
            player_counts[row["player"]] += 1
    write_rows(out / "candidates.jsonl", candidates)
    save_json(out / "game-groups.json", dict(split_by_game=split_by_game, cluster_by_game={uid: find(uid) for uid in games},
                                           event_keys=event_keys, long_prefix_keys=prefix_keys))
    # Only diagnostic training rows are made convenient to retrieve during implementation.
    tasks = []
    for phase in PHASES:
        tasks.extend([r for r in candidates if r["split"] == "train" and r["primary_phase"] == phase][:6])
    save_json(out / "training-probe-tasks.json", tasks)
    phase_games = Counter(split_by_game.values())
    report = dict(status="prepared_not_teacher_verified", games=len(games), grouped_components=len(clusters),
                  largest_group=max(map(len, clusters.values())), split_games=dict(phase_games),
                  public_worked_case_games_forced_to_development=len(public_case_games),
                  prior_board_keys_excluded=len(prior_keys), recognized_previous_game_ids=len(previous_games),
                  exclusions=dict(excluded), candidates=dict(chosen_counts), player_candidate_counts=dict(player_counts),
                  same_event_groups=len(event_seen), long_32ply_prefix_groups=len(prefix_seen),
                  cross_split_canonical_board_overlap=0, cross_split_recorded_family_overlap=0,
                  candidate_sha256=sha256(out / "candidates.jsonl"),
                  limits=["Event grouping uses normalized supplied event/site/year and may miss aliases or combine unrelated events.",
                          "Whole games, identical long opening prefixes, and recorded events are grouped; tactical/semantic near-duplicates cannot be ruled out.",
                          "Opening plies 1-12 are excluded rather than linking all games through the initial position.",
                          "Earlier 300k source-game IDs and some historic metadata are not recoverable; only recognized IDs and exact/mirrored exposed boards can be excluded.",
                          "Phase labels and source Elo/time controls remain factual or heuristic metadata, never inference inputs."])
    save_json(out / "audit.json", report)
    save_json(ROOT / "docs/evidence/threephase-data-audit.json", report)
    print(json.dumps(report, indent=2), flush=True)


def verify():
    config = json.loads(CONFIG.read_text())
    baseline = json.loads((RUN / "baseline/results.json").read_text())
    assert baseline["status"] == "complete", "Do not run the heavy teacher alongside baseline clock matches"
    out = RUN / "data"
    candidates = read_rows(out / "candidates.jsonl")
    audit = json.loads((out / "audit.json").read_text())
    assert sha256(out / "candidates.jsonl") == audit["candidate_sha256"]
    cache_path = out / "verification-cache.jsonl"
    cache = {r["id"]: r for r in read_rows(cache_path)} if cache_path.exists() else {}
    queues = defaultdict(list)
    for row in candidates:
        queues[row["split"], row["primary_phase"]].append(row)
    targets = {(split, phase): count // len(PHASES) for split, count in config["phase_diagnostic_targets"].items() for phase in PHASES}
    accepted, counters, rejected = [], Counter(), []
    verifier = Verifier(SF, tuple(config["teacher_nodes"]))
    assert sha256(SF) == "45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0"
    try:
        while any(queues[key] and counters[key] < target for key, target in targets.items()):
            progressed = False
            for key, target in targets.items():
                if counters[key] >= target or not queues[key]:
                    continue
                row = queues[key].pop(0)
                if row["id"] not in cache:
                    if len(cache) >= config["maximum_teacher_attempts"]:
                        continue
                    verified, reason = verifier.verify(row)
                    entry = dict(id=row["id"], verified=verified, reason=reason)
                    with cache_path.open("a", encoding="utf-8") as stream:
                        stream.write(json.dumps(entry, separators=(",", ":")) + "\n")
                    cache[row["id"]] = entry
                progressed = True
                entry = cache[row["id"]]
                if entry["verified"]:
                    accepted.append(entry["verified"])
                    counters[key] += 1
                else:
                    rejected.append(dict(id=row["id"], reason=entry["reason"]))
                if (len(accepted) + len(rejected)) % 24 == 0:
                    print(f"verified {len(accepted)} accepted, {len(rejected)} quarantined", flush=True)
            if not progressed:
                break
    finally:
        verifier.close()
    write_rows(out / "verified.jsonl", accepted)
    save_json(out / "rejections.json", rejected)
    keys, families = defaultdict(set), defaultdict(set)
    pv_count = 0
    for row in accepted:
        keys[row["split"]].add(duplicate_key(chess.Board(row["solver_fen"])))
        families[row["split"]].add(row["family_id"])
        for analysis in row["candidate_moves"]:
            for move in analysis.values():
                board = chess.Board(row["relevant_history"]["start_fen"])
                for uci in row["relevant_history"]["moves"] + move["pv"]:
                    board.push_uci(uci)
                pv_count += 1
    for a, b in [("train", "validation"), ("train", "test"), ("validation", "test")]:
        assert not keys[a] & keys[b] and not families[a] & families[b]
    report = dict(status="complete", intended_targets={f"{a}:{b}": v for (a, b), v in targets.items()},
                  accepted={f"{a}:{b}": counters[a, b] for a, b in targets}, positions=len(accepted),
                  targets_met=all(counters[k] == v for k, v in targets.items()),
                  confidence=dict(Counter(r["confidence"] for r in accepted)), quarantined=len(rejected),
                  teacher_attempts=len(cache), teacher_binary_sha256=sha256(SF), teacher_nodes=config["teacher_nodes"],
                  legal_pvs_replayed=pv_count, exact_cross_split_boards=0, recorded_cross_split_families=0,
                  verified_sha256=sha256(out / "verified.jsonl"),
                  learning="Diagnostic train partition supports engineering/validation only. This script does not fit or modify a neural network.")
    save_json(out / "manifest.json", report)
    save_json(ROOT / "docs/evidence/threephase-verified-manifest.json", report)
    print(json.dumps(report, indent=2), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=["prepare", "verify"], required=True)
    args = parser.parse_args()
    prepare() if args.stage == "prepare" else verify()


if __name__ == "__main__":
    main()
