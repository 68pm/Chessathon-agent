"""Incremental teacher-corrected policy learning with a matched outcome-free ablation."""

import os

for variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
    os.environ[variable] = "1"

import copy
import hashlib
import json
import re
import time
from collections import Counter

import chess
import numpy as np

from engine.player_policy import SIZE
from nn.model import Network
from nn.optim import Adam
from scripts.alien_rating_ladder import save_json, sha256
from training.elite_cases import CONFIG, RUN
from training.fastchess_data import ROOT, read_rows
from training.puzzle_data import digest
from training.puzzle_train import batch, encode_rows, evaluate, masked_target_loss
from training.puzzle_verifier import duplicate_key
from training.train import checkpoint


def outcome_target(row, maximum=0.1):
    """Reinforce a sound played move after a win/draw; keep losing errors teacher-corrected."""
    target = dict(row["target_distribution"])
    reward = float(row.get("training_game_score", 0))
    if not 0 <= reward <= 1 or not 0 <= maximum <= 0.1:
        raise ValueError("Reward/mixing coefficient outside the declared bounded range")
    move = row.get("played_uci")
    alpha = maximum * reward if move in row["acceptable_first_moves"] else 0.0
    if alpha:
        target = {key: (1 - alpha) * value + (alpha if key == move else 0) for key, value in target.items()}
    assert np.isclose(sum(target.values()), 1) and min(target.values()) >= 0
    return target, alpha


def prepare_rows(game_reviews):
    ordinary = read_rows(ROOT / "runs/carlsen-curriculum-20260906/data/curriculum.jsonl")
    phase = read_rows(ROOT / "runs/threephase-pilot-20260906/data/verified.jsonl")
    puzzles = read_rows(ROOT / "runs/puzzle-pilot-20260906/data/verified.jsonl")
    cases = read_rows(RUN / "cases/verified.jsonl")
    broad = sorted([r for r in ordinary if r["split"] == "train"], key=lambda r: digest(r["fen"]))[:2048]
    validation = {
        "broad": sorted([r for r in ordinary if r["split"] == "validation"], key=lambda r: digest(r["fen"]))[:128],
        "phase": [r for r in phase if r["split"] == "validation"],
        "puzzle": [r for r in puzzles if r["split"] == "validation"],
    }
    def key(row):
        return duplicate_key(chess.Board(row.get("solver_fen", row.get("fen"))))
    forbidden = {key(r) for group in validation.values() for r in group}
    def source_game(row):
        match = re.search(r"/game/live/(\d+)", row.get("source_url", ""))
        return match.group(1) if match else row.get("source_game_id", row.get("game_id"))
    forbidden_games = {source_game(r) for group in validation.values() for r in group} - {None}
    # Every available public case is an engineering/training example. It is never advertised as a new held-out test.
    knowledge = cases + [r for r in phase + puzzles if r["split"] == "train"]
    games = [r for review in game_reviews for r in review if r["split"] == "train"]
    used, rows, pools = set(), [], {}
    exclusions = Counter()
    # Prefer the most recent game record when an adaptation position has recurred.
    for label, group in [("games", list(reversed(games))), ("knowledge", knowledge), ("broad", broad)]:
        pool = []
        for row in group:
            row = dict(row)
            row.setdefault("family_id", "source-game:" + str(row.get("game_id", row.get("source_game_id"))))
            row.setdefault("id", "board:" + digest(row.get("solver_fen", row.get("fen"))))
            board_key = key(row)
            if board_key in forbidden or board_key in used or source_game(row) in forbidden_games:
                cause = "validation_source_game" if source_game(row) in forbidden_games else "validation_collision" if board_key in forbidden else "training_duplicate"
                exclusions[cause] += 1
                continue
            if label == "games" and chess.Board(row["solver_fen"]).ply() <= 12:
                exclusions["early_game_training_prefix"] += 1
                continue
            assert row["split"] == "train"
            used.add(board_key)
            pool.append(len(rows))
            rows.append(row)
        pools[label] = np.array(pool, dtype=int)
    groups = {}
    training_count = len(rows)
    for name, group in validation.items():
        assert group
        groups[name] = np.arange(len(rows), len(rows) + len(group))
        rows.extend(group)
    return rows, pools, groups, training_count, exclusions


def fit(stage, initial_policies, game_reviews):
    config = json.loads(CONFIG.read_text())
    input_hashes = {name: sha256(ROOT / name) for name in [
        "runs/carlsen-curriculum-20260906/data/curriculum.jsonl", "runs/puzzle-pilot-20260906/data/verified.jsonl",
        "runs/threephase-pilot-20260906/data/verified.jsonl", "runs/elite-case-pilot-20260907/cases/verified.jsonl"]}
    input_hashes["game_reviews"] = hashlib.sha256(json.dumps(game_reviews, sort_keys=True).encode()).hexdigest()
    out = RUN / "training" / stage
    if (out / "report.json").exists():
        old = json.loads((out / "report.json").read_text())
        assert old["status"] == "complete", "Inspect incomplete training before replaying a stage"
        assert old["initial_sha256"] == {name: sha256(path) for name, path in initial_policies.items()}
        assert old["input_hashes"] == input_hashes and old["source_sha256"] == sha256(__file__)
        return old
    assert not out.exists(), "Preserve incomplete training checkpoints"
    out.mkdir(parents=True)
    rows, pools, groups, training_count, exclusions = prepare_rows(game_reviews)
    assert len(pools["broad"]) >= config["examples_per_epoch"]
    encoded = encode_rows(rows)
    reward_rows = copy.deepcopy(rows)
    boosts = []
    for i in pools["games"]:
        reward_rows[i]["target_distribution"], alpha = outcome_target(rows[i], config["maximum_outcome_target_mix"])
        if alpha:
            boosts.append(dict(id=rows[i]["id"], score=rows[i]["training_game_score"], alpha=alpha))
    reward_encoded = list(encoded)
    for i in pools["games"]:
        reward_encoded[i] = encode_rows([reward_rows[i]])[0]
    count_epochs = config["seed_epochs"] if stage == "seed" else config["update_epochs"]
    rng = np.random.default_rng(config["seed"] + len(game_reviews))
    orders = []
    for _ in range(count_epochs):
        chosen, exposure, families = [], Counter(), Counter()

        def sample(pool, count):
            initial_count = len(chosen)
            for _ in range(config["maximum_position_exposures_per_epoch"]):
                for i in rng.permutation(pool):
                    family = rows[i]["family_id"]
                    if exposure[i] >= config["maximum_position_exposures_per_epoch"] or families[family] >= config["maximum_game_exposures_per_epoch"]:
                        continue
                    chosen.append(int(i))
                    exposure[i] += 1
                    families[family] += 1
                    if len(chosen) - initial_count >= count:
                        return

        if len(pools["games"]):
            sample(pools["games"], 192)
        # Put source cases first once, then sample the broader verified phase/puzzle curriculum.
        case_ids = np.array([i for i in pools["knowledge"] if rows[i].get("origin_type") == "supplied_elite_case"], dtype=int)
        if len(case_ids):
            sample(case_ids, len(case_ids))
        sample(pools["knowledge"], 320 - min(len(case_ids), 320))
        sample(pools["broad"], config["examples_per_epoch"] - len(chosen))
        assert len(chosen) == config["examples_per_epoch"] and max(chosen) < training_count
        rng.shuffle(chosen)
        orders.append(chosen)
    sampled_ids = {rows[index]["id"] for order in orders for index in order}
    applied_boosts = [item for item in boosts if item["id"] in sampled_ids]
    save_json(out / "training-order.json", dict(ids=[r.get("id", r.get("game_id")) for r in rows],
              indices_by_epoch=orders, training_count=training_count,
              source_case_ids=[r["id"] for r in rows[:training_count] if r.get("origin_type") == "supplied_elite_case"],
              reward_boosts=applied_boosts, reward_targets_available=len(boosts), exclusions=dict(exclusions), validation_or_test_replay=0))
    report = dict(status="running", stage=stage, initial_sha256={name: sha256(path) for name, path in initial_policies.items()},
                  config_sha256=sha256(CONFIG), source_sha256=sha256(__file__), input_hashes=input_hashes, game_reviews=len(game_reviews),
                  reward_boosted_positions=len(applied_boosts), recipes={},
                  objective="Full-legal teacher-corrected supervised targets; outcome chain mixes at most 10% sound winning action (5% for a draw). No policy-gradient/off-policy RL claim; game result never becomes a position-value target.")
    for recipe in ["teacher_only", "outcome"]:
        destination = out / recipe
        destination.mkdir()
        net = Network.load(initial_policies[recipe])
        initial_arrays = [parameter.value.copy() for parameter in net.parameters()]
        optimizer = Adam(net.parameters(), lr=config["learning_rate"])
        initial_validation = {name: evaluate(net, encoded, ids) for name, ids in groups.items()}
        def selection_score(metrics):
            return sum(weight * metrics[key]["cross_entropy"] for key, weight in [("broad", .5), ("phase", .3), ("puzzle", .2)])
        best = selection_score(initial_validation)
        net.save(destination / "best.npz")
        chosen_epoch = 0
        logs = [dict(epoch=0, validation=initial_validation, selection_score=best)]
        started = time.perf_counter()
        training_data = reward_encoded if recipe == "outcome" else encoded
        for epoch, order in enumerate(orders, 1):
            if (ROOT / "STOP_TRAINING").exists():
                raise InterruptedError("STOP_TRAINING requested")
            accumulated = 0.0
            for offset in range(0, len(order), config["batch_size"]):
                ids = order[offset:offset + config["batch_size"]]
                x, mask, target = batch(training_data, ids)
                optimizer.zero_grad()
                logits = net.forward(x.reshape(-1, SIZE)).reshape(mask.shape)
                loss, grad = masked_target_loss(logits, mask, target)
                assert np.isfinite(loss) and np.isfinite(grad).all()
                net.backward(grad.reshape(-1, 1))
                optimizer.step()
                assert all(np.isfinite(p.value).all() for p in net.parameters())
                accumulated += len(ids) * loss
            validation = {name: evaluate(net, encoded, ids) for name, ids in groups.items()}
            metric = selection_score(validation)
            if metric < best:
                best, chosen_epoch = metric, epoch
                net.save(destination / "best.npz")
            checkpoint(destination / "last.npz", net, optimizer, epoch, rng)
            logs.append(dict(epoch=epoch, validation=validation, selection_score=metric,
                             mean_training_loss=accumulated / len(order), optimizer_steps=optimizer.t))
            save_json(destination / "metrics.json", logs)
        selected = Network.load(destination / "best.npz")
        distance = sum(float(np.square(p.value - initial).sum()) for p, initial in zip(selected.parameters(), initial_arrays, strict=True)) ** .5
        report["recipes"][recipe] = dict(best_policy=str((destination / "best.npz").relative_to(ROOT)),
                  sha256=sha256(destination / "best.npz"), selected_epoch=chosen_epoch,
                  parameter_l2_change=distance, epochs=logs, seconds=time.perf_counter() - started)
        save_json(out / "report.json", report)
        print(f"{stage}/{recipe}: selected epoch {chosen_epoch}, parameter change {distance:.6f}", flush=True)
    report["status"] = "complete"
    save_json(out / "report.json", report)
    return report
