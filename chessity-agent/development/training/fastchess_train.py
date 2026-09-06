"""Matched policy fine-tuning: broad replay versus verified fast-chess/graph/error mixture."""

import os

for variable in ["OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"]:
    os.environ[variable] = "1"

import json
import time
from collections import Counter

import chess
import numpy as np

from engine.player_policy import SIZE, PlayerPolicy
from nn.model import Network
from nn.optim import Adam
from scripts.alien_rating_ladder import save_json, sha256
from training.chess_curriculum import choose
from training.fastchess_data import CONFIG, ROOT, RUN, read_rows
from training.puzzle_data import digest
from training.puzzle_train import batch, encode_rows, evaluate, masked_target_loss
from training.train import checkpoint


def main():
    out = RUN / "training"
    if out.exists():
        raise ValueError("Fresh training output required")
    out.mkdir()
    config = json.loads(CONFIG.read_text())
    manifest = json.loads((RUN / "data/manifest.json").read_text())
    assert sha256(RUN / "data/verified.jsonl") == manifest["verified_sha256"]
    # No test example is encoded, scored, replayed or used to select an epoch.
    fresh = [r for r in read_rows(RUN / "data/verified.jsonl") if r["split"] != "test"]
    puzzles = [r for r in read_rows(ROOT / "runs/puzzle-pilot-20260906/data/verified.jsonl") if r["split"] != "test"]
    ordinary = read_rows(ROOT / "runs/carlsen-curriculum-20260906/data/curriculum.jsonl")
    broad = choose([r for r in ordinary if r["split"] == "train"], 4096, True, config["seed"])
    broad_validation = sorted([r for r in ordinary if r["split"] == "validation"], key=lambda r: digest(r["fen"]))[:256]
    rows = broad + broad_validation + fresh + puzzles
    encoded = encode_rows(rows)
    broad_ids = np.arange(len(broad))
    valid_broad = np.arange(len(broad), len(broad) + len(broad_validation))
    fresh_start = len(broad) + len(broad_validation)
    puzzle_start = fresh_start + len(fresh)
    fresh_ids = np.array([fresh_start + i for i, r in enumerate(fresh) if r["split"] == "train" and r["origin_type"] != "actual_observed_blunder_child"])
    valid_fresh = np.array([fresh_start + i for i, r in enumerate(fresh) if r["split"] == "validation"])
    puzzle_ids = [puzzle_start + i for i, r in enumerate(puzzles) if r["split"] == "train"]
    valid_puzzle = np.array([puzzle_start + i for i, r in enumerate(puzzles) if r["split"] == "validation"])
    initial_policy = PlayerPolicy(ROOT / config["initial_policy"])
    failures = []
    for i in fresh_ids:
        board = chess.Board(rows[i]["solver_fen"])
        moves = list(board.legal_moves)
        chosen = moves[int(np.argmax(initial_policy.logits(board, moves)))].uci()
        if chosen not in rows[i]["acceptable_first_moves"]:
            failures.append(int(i))
    replay = np.array(sorted(set(puzzle_ids + failures + [fresh_start + i for i, r in enumerate(fresh)
                             if r["split"] == "train" and r["origin_type"] == "actual_observed_blunder_child"])))
    assert len(fresh_ids) >= 2000 and len(valid_fresh) == 128 and len(replay) >= 154
    groups = {"broad": valid_broad, "bundle": valid_fresh, "puzzle": valid_puzzle}
    config = dict(config, initial_policy_sha256=sha256(ROOT / config["initial_policy"]),
                  data_sha256=manifest["verified_sha256"],
                  broad_source_sha256=sha256(ROOT / "runs/carlsen-curriculum-20260906/data/curriculum.jsonl"),
                  puzzle_source_sha256=sha256(ROOT / "runs/puzzle-pilot-20260906/data/verified.jsonl"))
    save_json(out / "config.json", config)
    save_json(out / "replay.json", {"training_only_ids": [rows[i]["id"] for i in replay],
              "test_and_validation_failures_used": 0,
              "cause": "Verified training mistakes or baseline raw-policy disagreement; no inferred psychological failure label."})
    report = {"status": "running", "config": config, "recipes": {},
              "architecture": "Existing 935-64-32-1 policy. Full-legal soft move targets; no new head or puzzle-value reward.",
              "compute": "Same initialization, optimizer updates, batch size and samples per epoch. Variable legal move counts mean arithmetic work and wall time are measured, not assumed identical."}
    initial = Network.load(ROOT / config["initial_policy"])
    report["baseline_validation"] = {key: evaluate(initial, encoded, ids) for key, ids in groups.items()}
    for recipe in ["control", "fastchess"]:
        destination = out / recipe
        destination.mkdir()
        net = Network.load(ROOT / config["initial_policy"])
        optimizer = Adam(net.parameters(), lr=config["learning_rate"])
        rng = np.random.default_rng(config["seed"])
        best, logs, orders = float("inf"), [], []
        started = time.perf_counter()
        for epoch in range(config["epochs"]):
            if recipe == "control":
                indices = rng.permutation(broad_ids)
            else:
                exposure, related = Counter(), Counter()

                def sample(pool, count):
                    chosen = []
                    for _ in range(4):
                        for i in rng.permutation(pool):
                            family = rows[i]["family_id"]
                            if exposure[i] >= 4 or related[family] >= 24:
                                continue
                            chosen.append(int(i))
                            exposure[i] += 1
                            related[family] += 1
                            if len(chosen) == count:
                                return np.array(chosen)
                    raise ValueError("Insufficient diverse training-only pool")

                mix = config["mixture_counts"]
                verified = sample(fresh_ids, mix["verified_bundle_and_graph"])
                errors = sample(replay, mix["verified_error_replay"])
                indices = np.concatenate([rng.choice(broad_ids, mix["broad"], replace=False), verified, errors])
                rng.shuffle(indices)
            assert len(indices) == config["examples_per_epoch"]
            orders.append(indices.tolist())
            train_loss, legal_count = 0, 0
            for offset in range(0, len(indices), config["batch_size"]):
                ids = indices[offset:offset + config["batch_size"]]
                x, mask, target = batch(encoded, ids)
                optimizer.zero_grad()
                logits = net.forward(x.reshape(-1, SIZE)).reshape(mask.shape)
                loss, grad = masked_target_loss(logits, mask, target)
                assert np.isfinite(loss) and np.isfinite(grad).all()
                net.backward(grad.reshape(-1, 1))
                optimizer.step()
                train_loss += len(ids) * loss
                legal_count += int(mask.sum())
            validation = {key: evaluate(net, encoded, ids) for key, ids in groups.items()}
            selection = sum(config["validation_weights"][key] * values["cross_entropy"] for key, values in validation.items())
            if selection < best:
                best = selection
                net.save(destination / "best.npz")
            checkpoint(destination / "last.npz", net, optimizer, epoch + 1, rng)
            log = dict(epoch=epoch + 1, train_loss=train_loss / len(indices), validation=validation,
                       selection_score=selection, optimizer_steps=optimizer.t, encoded_legal_moves=legal_count)
            logs.append(log)
            save_json(destination / "metrics.json", logs)
            print(json.dumps({"recipe": recipe, **log}), flush=True)
        save_json(destination / "training-order.json", {"rows": [r.get("id", r.get("game_id")) for r in rows],
                                                       "indices_by_epoch": orders})
        report["recipes"][recipe] = dict(seconds=time.perf_counter() - started, epochs=logs,
                                        best_sha256=sha256(destination / "best.npz"))
        save_json(out / "report.json", report)
    report["status"] = "complete"
    save_json(out / "report.json", report)


if __name__ == "__main__":
    main()
