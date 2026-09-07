# Experimental value network

<!-- ELITE_SESSION_START -->
## Current selected upload: chessity-agent v1.14

Use `../latest/chessity-agent.zip`. The completed phase and elite-learning experiments did not earn promotion. The final outcome candidate (v1.33) scored 1W/1D/14L at 2400 and 0W/5D/11L at 2600; its direct score against v1.14 was 5W/2D/9L. Neither consistency target was reached. Clock: **120+0.5**; selected read-only runtime checks passed.

The neural policy really was trained from 20 independently verified elite cases and prior replay, with per-game Stockfish review and bounded outcome supervision. The referenced full elite corpus was unavailable. See [current delivery and all 35 versions](../reports/DELIVERY.md), [elite results](../reports/ELITE_LEARNING_RESULTS.md) and [phase results](../reports/THREEPHASE_RESULTS.md). Training-case recognition is not a rating, and the newer version number does not establish a stronger agent.
<!-- ELITE_SESSION_END -->

Earlier fusion selection and its dated results are preserved in `../reports/FINAL_FUSION_RESULTS.md`.

<!-- MAGNUS_SESSION_START -->
## Magnus + Witty + Classical candidate

`candidates/classical-witty-magnus-v1.zip` adds a newly fitted neural move policy
trained on 99,934 positions from both players, using the unchanged
classical search and optional Alien preparation. Downloaded 9,694 available Magnus
games in 194 parts. In the fixed 92-game test, the highest checkmate victories were
MadChess 1700 and Stockfish
1700 nominal settings. Against
the previous combined agent it scored 5W/5D/2L.
The new candidate won more than it lost in the small direct comparison, but this does not establish a reliable strength improvement.
See `../reports/MAGNUS_MIXED_SESSION.md` for training, every rung, PGNs and limitations.
Use `Play-Magnus-Mix.ps1` for local play. Previous packages remain available.

<!-- MAGNUS_SESSION_END -->

## Combined candidate, 6 September 2026

`mixed-classical-witty-v1` uses the Classical evaluator at every search node and
the unchanged Witty player-policy weights for bounded root move preferences.
There is no new fitting or numerical averaging of incompatible models: Classical
has no learned dataset/weights to merge. The 300k value network remains saved in
earlier variants and is not loaded by this candidate.

Policy preferences are capped at 10cp; selective Alien preparation adds at most
15cp to a matching candidate move. All legal moves are searched, mate scores stay
unchanged, and the existing clock/check/material/phase guards still apply.
The standard pre-sacrifice position produced N5f3 in both package probes.

Completed 12 games versus Stockfish's nominal 1700 setting (4W/2D/6L) and 12 versus
Classical v2 (4W/5D/3L), at 30+0.3. This does not establish a clear strength gain
or an official Elo. No actual Alien sacrifice opportunities occurred in these
general-opening games. All 24 PGNs were replayed; 44 tests and 130 extracted-package
legal calls passed. See `../reports/COMBINED_AGENT_TEST.md` for full evidence.

## Completed 300k dataset run

The unattended job completed on 2026-09-05 at 17:31 London time. The dataset contains
300,000 deduplicated positions: 240,436 train, 28,176 validation and 31,388 held-out test,
across 368 ECO/source groups. These are positions, not 300,000 games. The importer
scanned 771,539 games (77,270 annotated) and read 249,566,800 compressed bytes of the
same July 2026 CC0 Lichess export. All fifteen sampling buckets reached 20,000 positions.

The 775-128-32-1 architecture and training recipe below were used from random
initialisation. Best validation epoch 8 of 12 completed; validation MSE 0.106637,
held-out MSE 0.114548 and MAE 0.219303. Zero-predictor test MSE 0.430189.
Sparse/dense maximum prediction difference 4.47e-7. The 64-unit candidate's best
validation MSE was 0.108308, so the 128-unit model was selected by validation.
Comparing test errors across different dataset sizes is descriptive, because their
held-out position sets differ. Lower prediction error does not establish stronger play.

Exported model: `models/value-300k.npz`, 415,394 bytes, 103,489 parameters.
Weights SHA-256: `f82f9e7ac4c4ae983cf0f342dda838020fe05640eb4890d73210a326a5db1117`.
Dataset SHA-256: `a1ee5965271bd1aacf57c8c010bb2a63a9dfa746bea94f7d63612f4a57ad8daa`.
Original checkpoints, optimiser state, data and full logs are under
`runs/unattended-20260905-away/`. Portable evidence is in `../reports/evidence/300k/`.

At 3+0.05 versus classical v2, neural scored 1W/5D/6L and hybrid scored 3W/4D/5L.
Neither passed the promotion screen. `Play-300k.ps1` runs the trained hybrid locally;
`Play-Alien.ps1` adds the experimental prepared opening. The selected competition
package remains the classical champion. See `../reports/RATING_AND_300K.md` for the later
external-opponent benchmark and its rating limitations.

Stockfish 19 was subsequently installed outside this project for offline matches and
opening analysis. It did not generate or modify this network's training labels or weights.
This value network uses no Witty_Alien training data. The Alien repertoire is explicit
opening preparation. A subsequent separate move-ranking policy was added after the
user confirmed written Chess.com authorisation on 6 September 2026; its training
and fresh match results are recorded in `../reports/WITTY_TRAINING_SESSION.md`.

## Player move-preference network

The separate policy uses 935 mover-canonical board/move features and original
935-64-32-1 clipped-ReLU layers (62,017 trainable parameters). It learns recorded
player choices using masked cross-entropy against up to four uniformly sampled legal
alternatives. It starts from random weights; no published chess network is loaded.
The existing 300k value evaluator is retained. At runtime the policy adds a bounded
20-centipawn preference at the root of search, with phase/check/clock/material guards.
It changes move preferences, not the learned value targets. An explicit Alien opening
repertoire remains separately enabled in the experimental candidate.

This session used 50,000 decisions: 40,015 train, 4,981 validation and 5,004 test.
Training stopped after six epochs without further validation-loss improvement and
kept epoch three. Held-out sampled-choice accuracy was 72.10%; on 1,000 positions
with all legal alternatives, top-one agreement was 43.0% (uniform choice 5.68%)
and top-three agreement was 68.7%. These are imitation metrics, not tactical accuracy.
Policy SHA-256: `30b5175d18f29084032a89b08a0e9c85853dece6511c05a441ffada519fae775`.

The data snapshot contains 166,438 raw records across 129 monthly archives. Of the
165,486 PGNs, 164,388 are matching standard-chess games and 1,098 are other variants.
The 952 records without PGN are bughouse games; their raw records remain saved.
No records were silently filled with invented moves or value labels.

## Preserved first 50k experiment

Status: trained locally from random initialisation, **not selected for the default
competition runtime**. No published chess network was loaded or fine-tuned.

Architecture: 775-128-32-1, 103,489 float32 parameters, clipped ReLU hidden layers,
linear value output. Feature conventions are in ENGINE_SPEC.md. The canonical mover
bit is constant; castling, legal en passant and phase remain explicit.

Data: 50000 positions from annotated July 2026 Lichess standard games.
Source: https://database.lichess.org/standard/lichess_db_standard_rated_2026-07.pgn.zst. [Lichess releases these exports as CC0](https://database.lichess.org/).
The bounded importer read 39191425 compressed bytes, examined
120418 games and found 12420 annotated games.
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
No local teacher was used for this training run. This is not a WDL probability-calibrated model.

Training: custom NumPy backpropagation, Huber delta 0.25, Adam lr 0.001, betas 0.9/0.999,
epsilon 1e-8, L2 gradient penalty 1e-5, batch 256, seed 20260905. Validation-selected
epoch 5; run stopped after epoch 9. CPU only, one BLAS thread.

Held-out MSE 0.154291, MAE 0.287220; always-zero predictor MSE
0.412231. These are bounded target units, not centipawns or Elo.
Calibration bins are in ../reports/evidence/final-model-evaluation.json. Runtime parity error
was 3.28e-07. End-to-end repeated training produced identical weights.

Dataset SHA-256: `b24a2b31015a4d9df3362f0839f53209c2f26a77e5e400928c6f62256f9b6f64`.
Weights SHA-256: `15904469559e5e6dd6a46bdb1c815bc9cc95b86d8b1db27836d44feefaaf954f`.
Training command: `python -m training.train --epochs 16 --out runs/value-128`.
Export: `python -m training.export --checkpoint runs/value-128/best.npz`.

Limitations: chronological prefix and annotation selection bias; unknown teacher depth;
small capacity; limited training sample; neural cost reduces search depth. Hybrid lost
2W/1D/9L against classical v1; neural-only scored 2W/1D/3L in a smaller rejection screen.
Neither result supports replacing the classical champion.

Other completed ablations: 64-unit first hidden layer, hard-example mining, curriculum,
and auxiliary king-pressure learning. See ../reports/RESULTS.md; the auxiliary head is stripped
at export. Active external training labelling remains a future experiment. The completed
300k expansion is documented above. Training data and experimental weights do not appear
in the selected classical submission.zip.

<!-- CURRICULUM_SESSION_START -->
## Phase curriculum pilot

The controlled phase-coverage experiment is complete. Do not adopt this pilot as an improvement; it showed a regression in the small comparison. See `../reports/CARLSEN_CURRICULUM_RESULTS.md` for the 32-game comparison, validation counts, scope and reproduction steps. Candidate and equal-compute control are preserved separately; neither automatically replaces the baseline.
<!-- CURRICULUM_SESSION_END -->
