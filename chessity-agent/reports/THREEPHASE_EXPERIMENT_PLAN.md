# Three-phase improvement cycle — declared before new candidate outcomes

Baseline: preserved chessity-agent v1.14 (`candidates/classical-witty-magnus-v1`). Its locally trained 935–64–32–1 policy supplies a bounded root preference to classical search. Original weights and runtime folders remain frozen. Previous v1.23 is retained as a second comparison opponent. The earlier measured 2200 result for v1.14 was 1W/4D/7L; it is a nominal engine-setting result, not a human rating.

The supplied three-phase pack has 1,838 replayed games and 107,439 observations. All 38 supplied file checksums passed. The supplied validator was inspected and run: 402 principal variations and 3,810 reference opening lines were legally replayed. There are 2,047 disclosed cross-split board keys. Factual human moves and the 58 finite-search examples are not automatically reliable training targets. Original supplied validation output is preserved separately from this run's validation evidence.

## Sequence and finite budget

1. Audit source/phase coverage, preserve the baseline and environment, and run 12 fresh baseline games: four each against Stockfish 19 settings 2200, 2400 and 2600 at exactly 120+0.5. No candidate change is inferred from a win alone.
2. Build a small history-aware diagnostic pool from the pack, grouped by source game and event. Exclude previously exposed boards, their colour mirrors, supplied cross-split overlaps, and public worked-case answers from fresh assessment. Review near-duplicate continuation signatures and source-event overlap. Missing old source-game IDs remain a limitation.
3. Inspect baseline search cost and phase errors. First hypothesis: avoid unnecessary quiet-move enumeration in quiescence and use principal-variation search to reach stronger decisions in the same clock budget without changing minimax semantics. These are independently written improvements to this project's engine, not imported engine code.
4. If correctness and validation support it, examine one second bounded candidate using conservative late-move reductions with full-depth re-search when a reduced move improves alpha. Exclude forcing/check/late-endgame cases from reductions. This is selective search and must earn its place through validation; no strength gain is presumed.
5. At most two implementation candidates; at most 1,000 teacher attempts at 80k/320k nodes, targeting 192 diagnostic-training, 96 validation and 96 test positions across four phase groups. Teacher estimates remain offline. Use the existing compatible policy; only add a separate weight-training experiment if the diagnosis supports one. Reading the guides alone does not train weights.
6. Each surviving candidate receives eight development games against v1.14 with reversed colours. Development/validation results select at most one challenger. Fresh confirmation is 16 games against v1.14 plus eight against v1.23. Promotion requires a whole-colour-pair bootstrap 95% lower score bound above 50% against v1.14, at least 50% against v1.23, and no challenger runtime failure. Otherwise retain v1.14.
7. Complete 36 fixed final rated games, 12 each at 2200, 2400 and 2600, on the chosen challenger or retained baseline if no challenger passes correctness. Report that candidate's results even if it is not promoted. Finish the declared schedule regardless of whether a 2600 win occurs. Do not add games solely to obtain one.

The maximum full-game budget is 88 games across baseline, two development candidates, confirmation and final rated stages. Two local games run concurrently; each chess engine uses one thread, no pondering, and recorded host load. Avoid concurrent heavy teacher/training work during clock matches. This is several hours of local work, with checkpoints and fixed-stage resume commands. No paid compute, new service permissions or unrelated application changes.

Before any new validation outcomes, the selection tie-break is fixed: rank correctness-passing candidates by development match points, then total acceptable choices on the two validation clock modes, then fewer verified blunders on those modes, then fixed-node acceptable choices. Exact ties favour the simpler PVS candidate. This chooses a challenger for fresh confirmation; it does not itself promote an agent.

The separate phase-drill configuration adds at most 12 games, six each for the frozen baseline and selected challenger: four basic queen/rook conversion drills including colour mirrors, and two held-out practical endings with a near-zero finite teacher estimate. They use 120+0.5 against the 2600 setting and play to an actual result; there is no engine-score adjudication or tablebase claim. This brings the overall game cap to 100. Phase drills do not count as initial-position rated wins.

Measured baseline profile: eight diagnostic-training positions at 2,000 nodes completed depths 1–3. Legal-move generation accounted for about 41% of profiled total time, including both quiet and tactical moves; quiescence accounted for roughly 92% inclusive time. These overlapping profile categories must not be added together. Profiling overhead means these timings are cost-attribution evidence rather than uninstrumented throughput. The first implementation targets unnecessary quiet generation within that measured bottleneck.

## Specialist passes and assessment

Opening: preserve the optional Alien hint and existing training graph; audit the new pack's broader lines as references. Measure opening exits and deviations, including a book-disabled diagnostic. No claim that the partial training graph is a complete repertoire.

Middlegame: use verified quiet, forcing and defensive positions; report multiple acceptable moves and 200cp errors separately. Inspect the actual opponent response to alleged tactical resources. Do not reward checks or sacrifices on appearance.

Endgame: retain rule state, check stalemate and repetition before scores, and test basic conversion and draw preservation through complete continuations. Finite engine estimates are not exact WDL; no tablebase claim without a real permitted tablebase. Late-move reductions must be disabled in pawn/low-material endings to limit zugzwang and tempo risks.

The critic pass is sequential code/label review against explicit tests. No extra agent or private chain-of-thought dataset is required. Learner test inputs contain board/history and clock only; hide player, result, phase label and teacher answer. Public case studies are development material, never an unseen test. Reuse original broad training data if later fitting is justified, so a phase module does not erase previous coverage.

Record legal validation, phase source ledger, leakage exclusions, finite-label uncertainty, completed-depth/nodes/latency, held-out first-move quality and continuation results, all PGNs/clocks, source hashes, and W/D/L with uncertainty. Test read-only inference with network and subprocess access blocked. Current competition rules allow own source/weights and offline engine labels; they prohibit shipping third-party engines or teacher lookup databases. [Official rules and interface](https://aichessathon.com/docs).

## Resume

Initial baseline: `python -m scripts.threephase_matches --stage baseline --resume`.
First improvement controller after an interrupted/failed stage: `python -m scripts.threephase_first_cycle --resume`.
Candidate stage: `python -m scripts.threephase_matches --stage development --candidate candidates/NAME --resume`.
Frozen match resumes require unchanged configuration, candidate hashes and referee sources. A completed stage is not rerun. Original data and rejected candidates remain available.
