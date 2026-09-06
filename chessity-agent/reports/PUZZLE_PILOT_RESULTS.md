# Verified puzzle and blunder pilot

**Decision: Retain as a provisional candidate for further comparison; the small production test improved, but raw-policy blunders increased and strength is not established.** This is a 320-position pilot, not a 10,000-puzzle run or a demonstrated Elo increase. The experimental upload package is `candidates/puzzle-mixed-v1.zip`; the ordinary-data control is `candidates/puzzle-control-v1.zip`.

## Data and verification

The supplied brief is preserved in `PUZZLE_TRAINING_PROMPT.md`. The importer streamed only 2,500 source CSV rows from the [CC0 Lichess puzzle database](https://database.lichess.org/#puzzles), parsed columns by name, applied the opponent's setup move before the solver move, and replayed every source continuation. The version, response headers, compressed-prefix hash and subset hash are in the acquisition manifest. Sampling used a bounded prefix and family-stratified ordering; it is not uniform over the database.

The final pilot contains 228 Lichess puzzles, 34 positions from actual earlier local games, 46 independently verified legal branches, and 12 constructed KQK examples kept entirely in training. Board validity is not asserted to prove historical reachability for constructed examples. Linked mistake and sound-alternative positions remain in the same source-game family. Not every attempted three-position family survived verification; no unverified third position is treated as tactic-free.

Counts: `{"train": 248, "validation": 36, "test": 36}`. Families: `{"mating_patterns": 73, "ordinary_negative_control": 57, "punish_blunder": 39, "fundamental_tactics": 41, "defence": 35, "quiet_ideas": 6, "endgame": 33, "combinations": 36}`. Colours: `{"white": 175, "black": 145}`. Exact and colour-mirrored transpositions were deduplicated before splitting. 399,719 prior canonical player/value positions were excluded. Groups were split by source game/family; constructed near-neighbours are training-only. The original value dataset did not retain every source game ID, so cross-source game-level independence cannot be proved. Other related positions may remain.

Stockfish 19 (SHA `45bc8e4969147db9c2eb533810637994619bff0eacc81ccfd9854394901bcbd0`), full strength, one thread and 32MB hash, separately analysed **every legal root move** with 80,000 and 320,000 total nodes per pass. Hash is cleared between passes. Actual nodes and legal principal variations are retained. Seventy-three short mates were proved exhaustively against all legal defences within one or three plies. A proof cutoff is unresolved. The other 247 records contain stable engine estimates; mate values are never silently converted into centipawns for their regret labels. Non-exact mate scores and unstable leading estimates were quarantined.

Independent replay checked 19,804 analysis lines and repeated all 73 exact proofs. Estimated acceptable alternatives lie within 70cp of the best at both budgets. A clear blunder loses at least 200cp at both budgets, from the same mover's perspective. Smaller inconsistent gaps remain uncertain; these thresholds do not prove game outcomes. Full histories are replayed where available; incomplete-history positions do not support repetition-dependent claims. No tablebases were used.

## Learning and actual execution

The existing 935–64–32–1 move-policy network receives a distribution over legal moves: uniform over every proved mating alternative for exact tasks, soft score-based targets for engine estimates. Motif tags, teacher scores, source IDs and solutions are excluded from inference inputs. The ordinary game-value network is untouched; task objectives are never relabelled as game victories. This is supervised learning, so no RL episode rewards, duplicate completion payments, critic or dense sacrifice/check bonuses were introduced.

Both models started from the frozen Magnus/Witty checkpoint. Each ran six epochs of 1,024 examples, 32-position batches, Adam and learning rate 0.0002. The control uses ordinary human-move imitation. The puzzle recipe uses 614 ordinary examples, 256 puzzle draws and 154 training-failure replay draws per epoch. Exposure is capped at four per position and 24 per puzzle family per epoch. Only training failures enter replay. Ordinary sampling retains the earlier phase-coverage data, but does not load the unsuccessful curriculum model's weights. Full-legal move counts differ, so the runs match update counts rather than claiming exactly equal floating-point work.

Checkpoint selection minimises 0.6 × broad-validation CE + 0.4 × puzzle-validation CE. Test positions were not encoded or examined for training or checkpoint selection. Actual training-loop times: `{"control": 6.0949063999869395, "puzzle": 5.361853399997926}` seconds. The accepted-record verification total was 285.14 seconds; this excludes rejected candidates, import, deduplication and replay audit. No measured throughput is extrapolated into an automatic large download or paid run.

## Held-out findings

| Model | Evaluation | Accepted / 36 | Clear blunders / 27 CP-scored | Mean CP regret | Exact mate continuations / 9 |
|---|---|---:|---:|---:|---:|
| baseline | raw_policy | 18 / 36 | 6 / 27 | 239.9 | 5 / 9 |
| baseline | production_agent | 29 / 36 | 2 / 27 | 85.9 | 9 / 9 |
| control | raw_policy | 18 / 36 | 7 / 27 | 246.7 | 5 / 9 |
| control | production_agent | 29 / 36 | 2 / 27 | 85.9 | 9 / 9 |
| puzzle | raw_policy | 19 / 36 | 9 / 27 | 293.6 | 6 / 9 |
| puzzle | production_agent | 30 / 36 | 1 / 27 | 62.3 | 9 / 9 |

These 36 held-out positions are a small grouped sample. The production improvement is one defensive position and one fewer clear blunder; the raw network's errors and false-positive attacks increased. This is mixed evidence, not proof of general tactical mastery or improved Elo. Some families contain only one or two test positions. Inference used the actual agent process at 4,000ms remaining clock, with its normal allocation; it did not receive four seconds per move. Search and runtime guards are unchanged, including bypassing neural preferences in check, low material phase and large evaluation imbalances. Both neural raw judgement and production choices are recorded; the teacher never chooses student moves.

Exact short-mate continuation results cover every defensive reply. Supplementary rollouts independently reverify later student choices against engine defence for up to three student decisions. Passing that short quality horizon remains a truncated game, not a solved longer puzzle or a win. Full conversion of general material advantages, opposition, fortress recognition, perpetual-check defence and long combinations has not been established. The known draw/underpromotion diagnostic set is reported separately and does not inflate the held-out score. Thirty readable training examples are in `PUZZLE_VERIFIED_EXAMPLES.md`.

## Full games and runtime

Against baseline: **5W/0D/3L**, eight games, pair standard error 0.125.

Against control: **4W/1D/3L**, eight games, pair standard error 0.15728821740147395.

Games used fixed colour-paired starts, 30+0.3 and a 400-ply cap. All 16 PGNs and their recorded results were replayed. These small matches do not calibrate a human or website rating. Known diagnostic passes: `{"baseline": 14, "control": 14, "puzzle": 14}` out of 14 per model. Rollout outcomes: `{"baseline:raw_policy:uncertain_gap": 3, "baseline:production_agent:uncertain_gap": 3, "baseline:raw_policy:verified_quality_failure": 4, "baseline:production_agent:verified_quality_failure": 2, "baseline:production_agent:unresolved": 2, "control:raw_policy:uncertain_gap": 2, "control:production_agent:uncertain_gap": 3, "control:raw_policy:verified_quality_failure": 5, "control:production_agent:verified_quality_failure": 2, "control:production_agent:unresolved": 2, "puzzle:raw_policy:uncertain_gap": 1, "puzzle:production_agent:uncertain_gap": 2, "puzzle:raw_policy:verified_quality_failure": 6, "puzzle:production_agent:verified_quality_failure": 2, "puzzle:production_agent:unresolved": 2, "puzzle:production_agent:quality_horizon_passed": 1}`.

Each extracted candidate ZIP passed 130 legal calls, including active-policy and optional-Alien checks. The runtime audit blocks file writes, networking and subprocess creation. The engine retains its own original search and trained weights; no verifier executable, teacher weights or evaluation lookup table ships. [Competition documentation](https://aichessathon.com/docs) permits training one's own network on labelled positions. Local validation is distinct from organiser Linux validation.

## Reproduction

Run from the project with its Python environment and fresh directories:

```powershell
python -m training.puzzle_data --out runs/puzzle-repeat/data --target 320
python -m scripts.audit_puzzle_data --data runs/puzzle-repeat/data
python -m training.puzzle_train --data runs/puzzle-repeat/data --out runs/puzzle-repeat/training
python -m scripts.puzzle_examples --data runs/puzzle-repeat/data --out runs/puzzle-repeat/examples.md
```

`configs/puzzle-pilot.json` freezes seed, architecture, budgets, learning rate and selection. `scripts/puzzle_session.py` records exact package, evaluation and paired-match commands; its dated outputs intentionally refuse overwriting prior evidence. The original bounded CSV subset and verification cache are retained locally. Subsequent source-database updates or engine timing differences may prevent byte-for-byte repetition; reuse the frozen dataset/checkpoints to reproduce assessments.

Evidence: `docs/evidence/puzzle-pilot-20260906-session.json`, two match JSONs/PGNs, and `runs/puzzle-pilot-20260906` for source subset, targets, quarantine, audit, RNG/optimizer checkpoints, training order, timings and all student attempts. Larger-scale training was not adopted automatically after this mixed pilot.
