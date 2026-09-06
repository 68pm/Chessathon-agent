# Hikaru/Gotham verified fast-chess pilot

**Selected upload: chessity-agent v1.14, `classical-witty-magnus-v1`.** The new candidate did not meet the promotion rule; the preserved best remains the recommended upload.

Selected ZIP SHA-256: `6d287209c28bba520a21ef49261af99543a167fb192ce15513102c883c503a56`. The ZIP in the parent outputs directory is the exact selected archive. No competition upload was performed.

## Data and architecture

The supplied pack was audited by replaying all 2,135 games, 93,786 named-player decisions and recorded post-move clocks, plus 556 opening reference lines. It contains 1,063 Hikaru and 1,072 GothamChess games; Hikaru is the GM source and Levy Rozman the IM source. None of these games uses 120+0.5. Their clocks remain observational metadata, not a learned time-allocation target.

The verified pilot contains 2000 new human-game training positions, 128 validation and 128 test positions, 388 train-only opening decisions, and 37 independently verified punishment positions paired with observed training blunders. 1842 of the 2256 human choices met the verifier's acceptable-move criterion; the other 414 use corrected soft alternatives. Counts describe this selected pilot, not all player games.

Stockfish 19 served only as an offline teacher, with one thread, 32MB hash and full-legal MultiPV at 80k and 320k nodes, cleared hash between passes. Estimates must agree under the existing puzzle verifier; unstable or non-exact mate scores are quarantined. Short forced mates are exact only when the exhaustive solver proves them. Scores use the root side's perspective. Drawing defence is never labelled as a won game.

The existing 935–64–32–1 policy starts from the preserved puzzle-trained Carlsen/Witty policy. Both control and candidate receive 8 epochs of 4096 examples, batch size 32 and learning rate 0.00015. Candidate exposure is approximately 60% broad Carlsen/Witty phase coverage, 25% verified bundle/graph and 15% verified training errors/puzzle replay. Exposure caps are four per position and 24 per related family per epoch. Validation, not test results, selects checkpoints with weights 0.60 broad, 0.25 new validation and 0.15 puzzle validation. Legal-move counts vary, so equal update counts do not imply identical FLOPs.

Validation selected control epoch 1 and candidate epoch 7. Thus the complete training runs have matched update budgets, while the selected checkpoints represent different numbers of updates. The saved training-order audit confirmed training-only replay; the largest observed per-board exposure in a candidate epoch was two, and the largest recorded-family exposure was 24. Earlier source-game identification limitations still apply.

The new runtime uses the original classical node evaluator, a bounded 10cp policy preference and the same optional 15cp Alien hint in all three new builds. The Alien sacrifice remains optional. Existing guards disable learned root preferences in check, late endgames, large static imbalances and tiny budgets; raw-policy gains there do not establish a production endgame improvement. Previously trained 300k value and fusion variants remain preserved and were included in the preceding six-agent comparison; incompatible network weights were not averaged. Broad phase concepts and verified move targets reuse the Carlsen and puzzle modules without importing the rejected phase-curriculum checkpoint.

## Opening and clock changes

Verified own-side graph counts: `{"caro_kann": 100, "italian": 100, "queens_gambit": 40, "qgd": 100, "fallback": 48}`. It stores actual-state keys, separate full history, multiple sound choices, verified opponent replies where resolved, sampled training-game reply frequencies, factual pawn/file structure, original study prompts and counterexamples. It is a partial curriculum, not a complete connected repertoire. See `FASTCHESS_OPENING_GRAPH.md`. The graph is training-only: no teacher move/evaluation lookup ships. Book-on/off for this graph is therefore inapplicable; training-board recall is reported separately from unseen-board and continuation tasks. No videos or transcripts were converted into training labels.

The adaptive controller retains a legal move, returns promptly for a single legal reply, reserves at least 30ms when available, modestly increases the allocation in check, and adjusts its soft deadline after completed iterations when choices or scores are unstable. A hard wall-clock stop remains. Board features and the value interface are unchanged. The static-clock ablation shares the candidate's exact policy weights. Equal-node tests disable clock adaptation to study judgement separately from practical speed.

The actual referee and UCI transport passed fractional-increment tests: 120,000ms initially, 500ms only after a legal on-time move, and `winc 500 binc 500`. A late move cannot be rescued by increment. Production position probes include 10,000ms, 2,500ms and 800ms remaining clocks; these are remaining game clocks, not fixed per-move budgets.

## Fresh paired matches at 120+0.5

| Opponent | W | D | L | Score | Paired bootstrap 95% interval |
|---|---:|---:|---:|---:|---|
| matched_control | 2 | 4 | 2 | 50.0% | [0.3125, 0.6875] |
| previous_best | 3 | 4 | 5 | 41.7% | [0.20833333333333334, 0.5833333333333334] |
| static_clock | 2 | 3 | 3 | 43.8% | [0.25, 0.625] |
| stockfish:1700 | 4 | 1 | 3 | 56.2% | [0.3125, 0.875] |
| stockfish:2000 | 1 | 2 | 5 | 25.0% | [0.0, 0.5] |
| stockfish:2200 | 0 | 2 | 6 | 12.5% | [0.0, 0.25] |

Highest Stockfish handicap setting the **new candidate** defeated in this test: **2000**. These are nominal engine settings, not measured Chess.com, FIDE or competition Elo. A highest individual win is not a stable rating. The earlier selected baseline's 2000/2200 results remain in `FINAL_FUSION_RESULTS.md`.

All 52 new game PGNs, move clocks, increments, start positions, results and frozen source hashes passed replay checks. Terminations: `{"checkmate": 36, "threefold_repetition": 14, "fifty_moves": 1, "insufficient_material": 1}`. The matched pairs and promotion rule were declared before outcomes. Intervals resample opening pairs; their small sample and any identical observations can understate uncertainty. Even promotion is provisional local evidence, not proof of strongest-possible or GM-standard play.

Host-wide average CPU use across individual games ranged from 39.3% to 64.9%, with median 45.3%. These counters include all applications and initialization; they do not establish isolated-core conditions or attribute timing failures to a particular process. Other applications were observed consuming substantial CPU during data verification. Node-budget verification stayed fixed; wall-clock match performance remains specific to the recorded local conditions.

Promotion decision: Paired-opening lower 95% score bound did not exceed 50% against the preserved best. Candidate scored below 50% against static_clock.

## Conditional rating estimate

To answer the user's estimate request, the existing fractional-score Elo fit is applied to the actual rated games. This is conditional on Stockfish's nominal handicap numbers behaving like Elo anchors. It is a descriptive performance estimate on that local scale, not a human, website or official competition rating. It does not enter the promotion rule. The broad band combines a colour-pair bootstrap with a Wilson score envelope, rounded outwards; it cannot cover calibration, hardware or model error.

| Build | Nominal handicap-scale estimate | Broad descriptive band |
|---|---:|---|
| new_candidate | 1788 | 1500 to 2100 |
| preserved_best | 1874 | 1600 to 2200 |

## Position quality and practical cost

| Model / mode / clock | Accepted | CP-scored | 200cp blunders | Mean deep regret | Median ms | p95 ms |
|---|---:|---:|---:|---:|---:|---:|---:|
| candidate:equal_nodes:None | 35/48 | 48 | 1 | 44.041666666666664 | 177.64 | 264.88 |
| candidate:opening_continuation:4000 | 29/41 | 41 | 2 | 51.21951219512195 | 517.93 | 668.25 |
| candidate:production:10000 | 39/48 | 48 | 3 | 41.666666666666664 | 778.54 | 1021.02 |
| candidate:production:2500 | 40/48 | 48 | 3 | 42.479166666666664 | 392.36 | 554.89 |
| candidate:production:800 | 39/48 | 48 | 3 | 48.125 | 338.41 | 392.24 |
| candidate:raw_policy:None | 87/128 | 128 | 17 | 92.859375 | 0.57 | 1.30 |
| matched_control:equal_nodes:None | 35/48 | 48 | 1 | 44.041666666666664 | 152.97 | 178.61 |
| matched_control:opening_continuation:4000 | 30/41 | 41 | 1 | 47.80487804878049 | 519.10 | 664.83 |
| matched_control:production:10000 | 41/48 | 48 | 2 | 35.333333333333336 | 756.24 | 994.74 |
| matched_control:production:2500 | 39/48 | 48 | 3 | 47.979166666666664 | 420.65 | 574.39 |
| matched_control:production:800 | 38/48 | 48 | 3 | 49.208333333333336 | 330.02 | 392.28 |
| matched_control:raw_policy:None | 86/128 | 128 | 18 | 96.7890625 | 0.76 | 1.38 |
| previous_best:equal_nodes:None | 35/48 | 48 | 1 | 44.041666666666664 | 158.57 | 185.27 |
| previous_best:opening_continuation:4000 | 30/41 | 41 | 2 | 49.292682926829265 | 493.39 | 682.93 |
| previous_best:production:10000 | 40/48 | 48 | 3 | 40.729166666666664 | 766.63 | 979.59 |
| previous_best:production:2500 | 39/48 | 48 | 3 | 48.125 | 422.29 | 566.99 |
| previous_best:production:800 | 38/48 | 48 | 3 | 49.208333333333336 | 338.64 | 392.19 |
| previous_best:raw_policy:None | 84/128 | 128 | 18 | 96.2109375 | 0.79 | 1.66 |
| static_clock:equal_nodes:None | 35/48 | 48 | 1 | 44.041666666666664 | 121.12 | 145.16 |
| static_clock:opening_continuation:4000 | 28/41 | 41 | 2 | 52.90243902439025 | 519.10 | 682.85 |
| static_clock:production:10000 | 39/48 | 48 | 4 | 49.375 | 758.06 | 1015.74 |
| static_clock:production:2500 | 39/48 | 48 | 3 | 43.3125 | 416.41 | 558.21 |
| static_clock:production:800 | 38/48 | 48 | 3 | 47.9375 | 347.52 | 392.45 |
| static_clock:raw_policy:None | 87/128 | 128 | 17 | 92.859375 | 0.70 | 1.43 |

Raw-policy recognition was 87/128 acceptable choices for the candidate, versus 84 for the preserved best and 86 for the matched control. Their verified 200cp error counts were 17, 18 and 18, respectively. Small count differences on this selected test set are descriptive, not proof of a general tactical improvement.

At the fixed node budget the candidate changed 0 of 48 moves relative to the preserved best. The probe loads each saved policy and preserves its bounded root preference; classical search and existing policy guards can dominate the decision. The three timed tests reuse the same 48 boards, so their 144 calls are not 144 independent positions. Sequential timing and throughput measurements also reflect changing host load and should not be interpreted as a causal speed gain from the training recipe.

Training-graph recall was 277/388 for the candidate, 278 for the preserved best and 275 for control. This measures recall of training boards; the separate continuation tasks and full games are the relevant checks of play beyond those examples.


### Existing opening hint on/off

The permitted handwritten Alien preference was also compared on/off on known opening positions, at equal nodes and at a 4,000ms remaining-clock input. The latter calls get_move directly and excludes wire overhead. This diagnostic does not count as held-out neural recognition or full-game strength evidence; the new verified graph remains offline training material.

| Mode / hint | Accepted | Verified 200cp errors | Prepared moves followed |
|---|---:|---:|---:|
| equal_nodes:on | 13/13 | 0 | 6 |
| equal_nodes:off | 13/13 | 0 | 5 |
| wall_clock:on | 13/13 | 0 | 7 |
| wall_clock:off | 13/13 | 0 | 4 |

The evidence JSON retains phase/task breakdowns and every move assessment. The six-ply `plan_unseen_continuation` task tests an unseen continuation, without claiming it exceeds the stored repertoire's depth. A separate `after_deepest_stored_line` diagnostic selects a verified test-game position strictly beyond the deepest stored graph decision for each family where one is available; missing families are explicit in `evaluation/opening-depth-coverage.json`. These cases reuse the held-out pool and are not independent extra games. Root recognition and short continuation quality do not prove full middlegame conversion or endgame mastery. Post-test loss analysis samples up to 48 positions; unresolved mate/unstable scores are retained as unresolved. These losses were never fed back into training.

## Leakage, reliability and reproducibility

Post-test diagnosis examined 48 sampled positions from losses: 27 received stable verified assessments and 21 remained unresolved. Among the resolved samples, 2 met the two-budget 200cp blunder criterion. This is a selected sample, not a count of every mistake or a causal explanation of the losses. The complete diagnosis is in `evidence/fastchess-loss-audit.json`; family depth coverage is in `evidence/fastchess-opening-depth-coverage.json`.

Benchmark wins and losses never update the network. All tested weights stay fixed; outcomes affect selection and the descriptive rating estimate only. The current learner uses verified move targets and corrective examples, not reinforcement-learning win rewards. Any future outcome training needs separate training games and fresh evaluation games.

Whole supplied games retain their split. Exact/mirrored boards shared across splits, earlier player/value/puzzle boards, and recognized earlier source games are excluded from the fresh assessment pool. Related punishment branches keep the source training family. The train-only graph avoids earlier held-out boards. The original 300k dataset lacks recoverable source-game IDs, so related-position, opening-family and unknown teacher-data overlap cannot be ruled out completely. This limitation is separate from the verified zero exact cross-split duplicates.

The selected ZIP passed another read-only probe at a 120,000ms input clock: import 687.17ms, observed peak memory 37232640 bytes. File creation, deletion, directory creation and renaming were blocked, along with network/process operations. It contains readable own source and locally trained weights, with no external engine or teacher lookup. These are Windows local audits, not the organiser's Linux validation.

`configs/fastchess-pilot.json`, `configs/fastchess-openings.json`, `training/fastchess_data.py`, `training/fastchess_train.py` and the `scripts/fastchess_*` modules define the experiment. The session records source hashes, verification cache, exact sampled orders, checkpoints, validation metrics, read-only probes, position assessments and complete games under `runs/fastchess-pilot-20260906`. Original sources and unsuccessful checkpoints are preserved. No paid compute was used.

Primary resource rules: [AI Chessathon](https://aichessathon.com/docs), [python-chess engine interface](https://python-chess.readthedocs.io/en/latest/engine.html), [CC0 opening-name reference](https://github.com/lichess-org/chess-openings). Opening names are classifications, not best-move evidence. The player pack has its own provenance; it is not represented as entirely CC0.
