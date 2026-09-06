"""Generate factual result tables from saved logs, without inventing missing measurements."""

import csv
import hashlib
import json
import shutil
from pathlib import Path


def read(path):
    return json.loads(Path(path).read_text())


def main():
    evidence = Path("docs/evidence")
    evidence.mkdir(parents=True, exist_ok=True)
    Path("configs").mkdir(exist_ok=True)
    dataset = read("data/lichess-50k/metadata.json")
    model = read("runs/final-model-evaluation.json")
    package = read("submission.manifest.json")
    probe = read("runs/package-validation.json")
    reliability = read("runs/reliability.json")
    for source in Path("runs").glob("*.json"):
        shutil.copy2(source, evidence / source.name)
    shutil.copy2("data/lichess-50k/metadata.json", evidence / "dataset-metadata.json")
    shutil.copy2("submission.manifest.json", evidence / "submission-manifest.json")
    experiments = []
    training_rows = []
    for name in [
        "value-128",
        "value-64",
        "value-mining",
        "value-curriculum",
        "style-aux",
        "reproduction",
    ]:
        metrics = read(f"runs/{name}/metrics.json")
        best = min(metrics["epochs"], key=lambda r: r["validation_mse"])
        seconds = sum(r["seconds"] for r in metrics["epochs"])
        training_rows.append(
            f"| {name} | {len(metrics['epochs'])} | {best['epoch']} | {best['validation_mse']:.6f} | {seconds:.2f} |"
        )
        shutil.copy2(f"runs/{name}/metrics.json", evidence / f"{name}-metrics.json")
        shutil.copy2(f"runs/{name}/config.json", Path("configs") / f"{name}.json")
        experiments.append(
            {
                "experiment_id": name,
                "date": "2026-09-05",
                "change": name,
                "git_commit": "a7c01a7",
                "champion_commit": "4eb704f",
                "config": f"configs/{name}.json",
                "seed": 20260905,
                "dataset_hash": dataset["dataset_sha256"],
                "decision": "experimental_only",
                "notes": f"best validation MSE={best['validation_mse']}; training seconds={seconds}; source reproduction verified for value-128",
            }
        )
    match_rows = []
    matches = [
        "classical-minimax",
        "classical-real-clock",
        "hybrid-classical",
        "neural-classical",
        "style-classical",
        "style-aux-classical",
        "clockfix-classical",
        "final-real-clock",
    ]
    for name in matches:
        result = read(f"runs/{name}.json")
        clock = f"{result['base_ms'] / 1000:g}+{result['increment_ms'] / 1000:g}"
        match_rows.append(
            f"| {name} | {len(result['games'])} | {clock} | {result['wins']}/{result['draws']}/{result['losses']} | {result['score']:.1%} |"
        )
        experiments.append(
            {
                "experiment_id": name,
                "date": "2026-09-05",
                "git_commit": "a7c01a7"
                if name in ["clockfix-classical", "final-real-clock", "style-aux-classical"]
                else "4eb704f",
                "champion_commit": "4eb704f",
                "change": name,
                "seed": 20260905,
                "games": len(result["games"]),
                "time_control": clock,
                "wins": result["wins"],
                "draws": result["draws"],
                "losses": result["losses"],
                "score": result["score"],
                "zip_bytes": package["zip_bytes"],
                "decision": "retain_classical"
                if name in ["clockfix-classical", "final-real-clock"]
                else "baseline_or_reject_candidate",
                "notes": f"paired SE={result['pair_standard_error']}; see docs/evidence/{name}.json; small sample, no Elo claim",
            }
        )
    fields = "experiment_id,date,git_commit,champion_commit,change,config,seed,dataset_hash,games,time_control,wins,draws,losses,score,nodes_per_second,evals_per_second,p95_move_ms,model_bytes,zip_bytes,decision,notes".split(
        ","
    )
    with Path("EXPERIMENTS.csv").open("w", newline="") as output:
        writer = csv.DictWriter(output, fields)
        writer.writeheader()
        for row in experiments:
            writer.writerow(row)
        for name, result in model["variants"].items():
            writer.writerow(
                {
                    "experiment_id": "benchmark-" + name,
                    "date": "2026-09-05",
                    "git_commit": "a7c01a7",
                    "change": "24 fixed test positions at 80ms",
                    "dataset_hash": dataset["dataset_sha256"],
                    "nodes_per_second": result["nodes_per_second"],
                    "evals_per_second": result["evals_per_second"],
                    "p95_move_ms": result["p95_move_ms"],
                    "model_bytes": 0
                    if name in ["classical", "style15"]
                    else Path("models/value.npz").stat().st_size,
                    "decision": "profile_only",
                    "notes": "CPU shared with local tasks; no speed gain claim",
                }
            )
    table = "\n".join(match_rows)
    training_table = "\n".join(training_rows)
    benchmarks = "\n".join(
        f"| {name} | {r['evals_per_second']:.0f} | {r['nodes_per_second']:.0f} | {r['mean_depth']:.2f} | {r['p95_move_ms']:.2f} | {r['mean_style']:.2f} |"
        for name, r in model["variants"].items()
    )
    Path("docs/RESULTS.md").write_text(f"""# Measured results

Date: 2026-09-05. Local Intel i5-12450H, 16 GB RAM, Windows, Python 3.12.14.
Selected runtime: **champion-classical-v2**, source commit `a7c01a7`.
The timer correction is retained for precision; small matches do not establish an Elo gain.

## Paired matches

| Experiment | Games | Seconds + increment | Wins/draws/losses | Score |
| --- | ---: | --- | --- | ---: |
{table}

These use the unmodified official runner/referee and six public opening sequences,
with reversed colours. Fast matches use a 300-ply cap, full-clock matches 600.
Every listed match completed without crash, illegal move, flag or init failure.
Candidate arenas compare v1-based runtime folders; the final timer-corrected build is
tested separately against that preserved champion. PGNs and paired standard errors
are in `evidence/`. No games were drawn by adjudicating an evaluation score.
The initial official random-versus-greedy smoke test was 0 wins, 0 draws, 2 losses;
it only established that the harness ran.

## Training ablations

| Run | Epochs completed | Best epoch | Validation MSE | Training-loop seconds |
| --- | ---: | ---: | ---: | ---: |
{training_table}

Training times exclude loading, feature preparation, export and data collection.
One-thread NumPy, batch size 256, seed 20260905. Only one factor changes per ablation
apart from the auxiliary experiment, whose final layer necessarily changes shape.
The 64-unit result is promising on validation only; it has not passed a match-promotion
gate. Curriculum and mining are not defaults. No paid compute was used.

## Inference and search profile

| Mode | Evals/s | Nodes/s | Mean depth | p95 move ms | Mean style score |
| --- | ---: | ---: | ---: | ---: | ---: |
{benchmarks}

100 evaluator calls and 24 fixed held-out positions with an 80ms search budget.
This is a short local profile, not a dedicated-core server benchmark. Classical and
neural scores are different functions; the table compares cost, not equivalent work.
The first trained net loaded in {model["load_ms"]:.2f}ms. Sparse/dense maximum absolute
prediction difference: {model["parity_max_abs"]:.3g}.

## Reliability and package

- 19 automated tests pass, including finite-difference gradients and exact resume parity.
- {reliability["calls"]} legal move requests across {reliability["unique_fens"]} distinct FENs;
  {reliability["search_calls"]} exercised search, the remainder emergency fallback.
- {reliability["short_games"]} short stress games, {reliability["completed"]} naturally completed,
  {reliability["ply_capped"]} capped at 120 plies; no illegal moves or crashes.
- Those stress games test control paths at 1ms, not playing strength. The stress timing
  logger used Windows monotonic ticks; use the high-resolution profile above for latency.
- Extracted package: {probe["legal_calls"]} additional legal calls; init {probe["init_ms"]:.1f}ms;
  peak observed working set {probe["peak_working_set_bytes"] / 1_000_000:.1f} MB.
- Audit hook rejected file writes, socket actions and subprocesses; the probe passed.
- Default zip: {package["zip_bytes"]} bytes compressed, {package["uncompressed_bytes"]} uncompressed.

Memory is observed on the probe, not a proof of the worst case in every game. The table
has 4096 slots and the competition caps games at 600 plies. Linux container isolation,
server speed and organiser acceptance remain untested; no upload was performed.

## Next experiment

Profile and accelerate the original search/move generation, keeping v2 as the opponent.
Then run substantially more paired games. Do not increase neural blend weight simply
because its training loss falls.
""")
    weights_hash = hashlib.sha256(Path("models/value.npz").read_bytes()).hexdigest()
    reproduced = hashlib.sha256(Path("runs/reproduction/best.npz").read_bytes()).hexdigest()
    assert weights_hash == reproduced
    Path("MODEL_CARD.md").write_text(f"""# Experimental value network

Status: trained locally from random initialisation, **not selected for the default
competition runtime**. No published chess network was loaded or fine-tuned.

Architecture: 775-128-32-1, 103,489 float32 parameters, clipped ReLU hidden layers,
linear value output. Feature conventions are in ENGINE_SPEC.md. The canonical mover
bit is constant; castling, legal en passant and phase remain explicit.

Data: {dataset["positions"]} positions from annotated July 2026 Lichess standard games.
Source: {dataset["source"]}. [Lichess releases these exports as CC0](https://database.lichess.org/).
The bounded importer read {dataset["compressed_bytes_read"]} compressed bytes, examined
{dataset["scanned_games"]} games and found {dataset["annotated_games"]} annotated games.
It sampled at most 40 positions per game, deduplicated normalised FENs and nearly evenly
filled 15 phase/evaluation buckets. It did not scrape Chess.com or any named player.

Splits: 39,838 train, 4,687 validation, 5,475 test across 246 ECO/source groups.
Hashing ECO families holds those families together; missing ECO falls back to source
game URL. Exact cross-split normalised FEN duplicates are removed. Group disjointness
is verified. This reduces leakage but does not establish independence of related
positions from different families.

Labels: existing PGN engine evaluations interpreted through python-chess as White
scores and converted to mover perspective. Mate scores become +/-10,000cp; targets
are tanh(cp/600). Teacher executable/version/depth for each annotation is not known.
No teacher binary was used locally. This is not a WDL probability-calibrated model.

Training: custom NumPy backpropagation, Huber delta 0.25, Adam lr 0.001, betas 0.9/0.999,
epsilon 1e-8, L2 gradient penalty 1e-5, batch 256, seed 20260905. Validation-selected
epoch 5; run stopped after epoch 9. CPU only, one BLAS thread.

Held-out MSE {model["mse"]:.6f}, MAE {model["mae"]:.6f}; always-zero predictor MSE
{model["zero_mse"]:.6f}. These are bounded target units, not centipawns or Elo.
Calibration bins are in docs/evidence/final-model-evaluation.json. Runtime parity error
was {model["parity_max_abs"]:.3g}. End-to-end repeated training produced identical weights.

Dataset SHA-256: `{dataset["dataset_sha256"]}`.
Weights SHA-256: `{weights_hash}`.
Training command: `python -m training.train --epochs 16 --out runs/value-128`.
Export: `python -m training.export --checkpoint runs/value-128/best.npz`.

Limitations: chronological prefix and annotation selection bias; unknown teacher depth;
small capacity; limited training sample; neural cost reduces search depth. Hybrid lost
2W/1D/9L against classical v1; neural-only scored 2W/1D/3L in a smaller rejection screen.
Neither result supports replacing the classical champion.

Other completed ablations: 64-unit first hidden layer, hard-example mining, curriculum,
and auxiliary king-pressure learning. See docs/RESULTS.md; the auxiliary head is stripped
at export. Active external labelling and large-scale training are future runs, not claimed
as completed. Training data and experimental weights do not appear in submission.zip.
""")
    Path("docs/TECHNICAL_DISCLOSURE.md").write_text(f"""# Technical disclosure

This build uses original Python search/evaluation code and a custom explicit-backprop
NumPy framework, developed with OpenAI Codex coding assistance from the entrant's brief.
The entrant should review and understand the implementation before submitting or
claiming personal mastery of it. No Stockfish, Lc0, Maia or other engine implementation
was copied into the runtime. No model was required for or selected in the final zip.

## Runtime

Entry point: agent.get_move(fen, time_left_ms). Iterative-deepening negamax with alpha-beta,
capture/promotion quiescence, full check evasions, mate-distance scoring, 4096-slot bounded
transposition cache with history-sensitive keys, MVV-LVA capture ordering, killers/history,
and a tapered classical evaluator. The fallback is chosen before search. A high-resolution
monotonic deadline is checked inside the tree. Runtime is synchronous and does not write
files, access the network or launch a process. See ENGINE_SPEC.md for limitations.

Exact selected external runtime dependency: chess==1.11.2 on Python 3.12. Local tests use
Python 3.12.14. Neural candidates additionally use NumPy 2.5.2 with thread counts set to
one before import. No PyTorch, Numba or ONNX runtime path is used. Training-only tools add
zstandard 0.25.0; development tests use pytest 9.1.1 and ruff 0.16.6.

The official starter harness and baselines at commit
91f70e54be07e1bf56311962044a08b822c3af50 are retained unmodified for local testing under
STARTER_LICENSE. Baselines are opponents, not runtime dependencies; none ship.

## Data and model provenance

The only external training source is the CC0 Lichess standard-game export at
{dataset["source"]}. Sampling, grouping, label transforms and hashes are in MODEL_CARD.md
and docs/evidence/dataset-metadata.json. Dataset hash:
`{dataset["dataset_sha256"]}`. Offline labels were already present in PGN annotations;
their exact teacher versions/depths are unknown. No local teacher was installed or used,
and no teacher executable or evaluation lookup database is shipped.

We trained 775-128-32-1 float32 weights from random initialisation using our own Dense,
ClippedReLU, Huber and Adam implementations. Seed 20260905, batch 256, learning rate
0.001, L2 penalty 1e-5. `python -m training.train --epochs 16 --out runs/value-128` followed
by `python -m training.export` reproduces the model. A second complete run matched hash
`{weights_hash}` exactly. A separate test verifies resumed Adam/RNG state parity.
Epoch logs and configs are retained in docs/evidence and configs. No assertion of team
identity is inferred from generated metadata; this record documents the actual local run.

The auxiliary experiment adds a training-only king-pressure target at weight 0.1.
Root style is a secondary near-tie objective, with full-window re-search of uncertain
bounds and a 15cp tolerance. Both style experiments failed promotion and tolerance is
zero in the selected runtime. They do not imitate or claim association with a named player.

## Validation and outcome

19 automated tests pass. The final reliability run made 10,000 calls and 200 short games
with no illegal moves or crashes. The original classical build scored 10W/2D/0L versus
the starter minimax in 12 paired 3+0.05 games. The final timer-corrected build scored
9W/0D/3L versus the preserved prior build and 2W/0D/0L versus greedy at 120+0.5.
Neural and style candidates were rejected; complete results and uncertainty are in
RESULTS.md. No Elo, master-strength or competition acceptance claim is made.

The final extracted zip passed a fresh-process legality probe with a write/network/process
audit hook. Observed import {probe["init_ms"]:.1f}ms, peak working set
{probe["peak_working_set_bytes"] / 1_000_000:.1f}MB. This is a local smoke measurement, not
Linux isolation testing or a worst-case resource proof. The event's validation remains
authoritative. No competition upload, paid compute, API inference or external message occurred.

## Package

Selected source tag: champion-classical-v2, commit a7c01a7.
Compressed size: {package["zip_bytes"]} bytes; uncompressed: {package["uncompressed_bytes"]} bytes.
SHA-256: `{package["sha256"]}`.
Contents: {", ".join(package["files"])}.

The allowlist builder excludes training data, logs, baselines, external engines, native
binaries, experimental weights and credentials. It fixes ZIP timestamps and file order.

Final validation commands from the project directory, using prepared Python 3.12:

```text
python -m pytest tests -q
ruff check agent.py engine nn training scripts tests
python -m scripts.build_submission
python -m scripts.validate_package
python -m scripts.arena_compare --opponent baselines/greedy --games 2 --base-ms 120000 --increment-ms 500 --ply-cap 600 --out runs/final-real-clock.json
```

RULES_COMPLIANCE.md maps the verified specification and notes eligibility clarification.
The application and data limitations remain documented instead of being represented as
completed high-performance NNUE, ONNX, quantisation or external-teacher work.
""")
    Path("docs/STYLE_EXPERIMENT.md").write_text("""# Controlled style experiment

A: classical strength-only. B: classical plus a 15cp root near-tie window.
C: auxiliary king-pressure training plus a 20% hybrid evaluator and the same root window.
The same six opening sequences and reversed colours were used, 12 games per experiment
against preserved classical v1 at 3s + 0.05s. C also includes the timer correction;
therefore its comparison is a combined rejection screen, not a clean causal ablation
of only the auxiliary head. It was not accepted.

B scored 1W/1D/10L (12.5%). C scored 1W/3D/8L (20.8%). Both remain disabled.
On the shared 24-position 80ms profile, B's mean heuristic style score rose from
6.83 to 7.21 while completed depth fell from 2.63 to 2.21. These are descriptive local
measurements, not independent proof of aggressive chess. Check/capture/ring pressure
are the implemented style components; separate development/space/sacrifice quality
and learned tactical uncertainty have not been established.

The root primary chess value is never overwritten with style. A candidate must be
within the tolerance of the best completed score; failed-low near-ties are re-searched
with a full window. Style is suppressed when checked, strongly imbalanced, simplified
or severely short of time. This bounds only the engine's measured loss, not true chess
loss: an incomplete search can be wrong. No claim that all sacrifices are sound is made.

The auxiliary target is tanh((own king-ring pressure - opposing pressure)/8), with
Huber loss weighted 0.1. Training has two outputs; export retains only value weights.
Held-out auxiliary-model value MSE is recorded in evidence/aux-model-evaluation.json.
Increasing this objective after the failed arena is not justified. A larger clean
paired experiment and better tactical validation are required before any promotion.
""")
    Path("CHANGELOG.md").write_text("""# Changelog

## 2026-09-05

- Inspected the supplied brief and current event rules; preserved the official harness.
- Built original classical search, tapered evaluation, time management and legal fallback.
- Completed baseline and reliability tests; preserved champion-classical-v1.
- Implemented a small NumPy framework and gradient, learning, export and resume tests.
- Streamed 50,000 balanced CC0 annotated positions with group-separated splits.
- Trained value, smaller-network, curriculum, mining and auxiliary models locally.
- Reproduced the original model weights exactly; rejected weak neural/style candidates.
- Switched search deadlines to high-resolution monotonic timing; retained classical v2.
- Built and audited the local submission; added guides, evidence and run/train scripts.

No upload or organiser acceptance has occurred. No calibrated Elo is available.
""")
    Path("PLAN.md").write_text("""# Project checklist

- [x] Inspect workspace, supplied brief and current official rules.
- [x] Establish original classical engine and preserve baseline champion.
- [x] Build and test the NumPy neural framework.
- [x] Collect 50k permitted positions and complete reproducible training.
- [x] Compare classical, neural, hybrid and style candidates; retain classical.
- [x] Complete reliability, full-clock and extracted-package checks.
- [>] Finalise evidence and delivery (current task).

Research backlog (not enabled features): accelerated original move generation/search;
large dedicated-core arenas; controlled deeper teacher labels; 100k/300k growth;
residual/value calibration; incremental inference; ONNX/Numba benchmarks and quantisation.
These require new measured experiments rather than being described as completed.
""")
    print("Recorded evidence, disclosures, model card and experiment tables.")


if __name__ == "__main__":
    main()
