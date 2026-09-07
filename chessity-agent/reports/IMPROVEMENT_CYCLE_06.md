# Cycle 06 — train verified alternatives, with a matched score-only control

Predeclared before endpoint verification or fitting. The incumbent remains v1.41.
Cycle05's completed comparison was2W/2D/4L; its rated screen/audit finish on the
existing fixed schedule. Small calculation-depth gains have not established a
stronger replacement. Do not mix the unpromoted search changes into a new network.

The first residual pilot improved static MSE but did not demonstrate a playing
gain. Its supplementary labels described roots; later error audits now provide
independently checked quiet successor positions for both the played and preferred
branches. Hypothesis: adding a pairwise preference loss to these score labels
will better preserve the verified advantage of the alternative, without harming
general value prediction. Use the existing768-input/32-clipped-ReLU/one-output
residual architecture and its own previously trained weights. This is supervised
counterfactual learning, not reward-based online reinforcement learning.

Data budget: retain the 8 existing verified pairs. After cycle05's controller is
complete, verify at most16 additional pairs from cycle04 and16 from cycle05 using
the existing80k/320k endpoint checks. At most25.6M requested new teacher nodes;
cache successes and quarantines, never relax acceptance criteria to increase count.
Restore actual history; exclude repeated/claimable/terminal/check endpoints and
exact/mirror collisions with the original 34k training/validation set. Group both
colours and all sources sharing an opening setup; provided ECO groups stay grouped.
Hold out whole groups deterministically. Require at least8 training pairs across
2 groups and4 held-out pairs in at least1 further group before a fit.
Use broad opening families where known (including shared Ruy Lopez/Petrov setups
across sources). Select a held-out group set using counts alone, closest to 25%
of pairs while meeting those minima; seeded hash order breaks ties. Never inspect
prediction errors to select groups. Exclude a whole pair when either endpoint
collides with another partition or any original residual-data position.

Fit budget: two matched models, six epochs each, same initial own residual weights,
same ordinary replay positions, order, optimiser and verified endpoint-score loss.
The candidate additionally learns a bounded100–200cp preference margin between
the two endpoint values, converted to the original mover's perspective. The control
has zero preference-loss weight. Add no new input features or architecture. Protect
the original 4000 validation positions. Fixed epochs; never select on held-out pairs.
Use batch256, Adam learning rate0.0003, endpoint-score weight0.25, pairwise-loss
weight0.10 (control0), and L2 weight0.00001. Both receive the same number of updates.

Pilot gate: all outputs finite; runtime/gradient signs and clipping verified;
candidate ordinary capped-MSE no more than 1% worse than the matched control and
initial model; candidate held-out pair-margin loss strictly lower than control,
with no worse held-out ordering accuracy. Report every metric even on failure.
This is a small development gate, not proof of reduced game blunders or an Elo gain.
Only a passing pilot may be frozen in otherwise identical v1.41 runtimes and receive
read-only/speed probes, matched games against its score-only control and v1.41, then
2400/2600 screens. Predeclare that later match schedule after inspecting the pilot.
Do not auto-promote or merge from a static-loss improvement alone.

The pilot passed its predeclared static gate. All 18 verified pairs survived the
additional collision/history filters. Count-only grouping assigned12 training pairs
across French, Italian, Slav and Petrov families, with 6 Ruy Lopez pairs held out.
Both models completed exactly6 epochs from the same own initial weights and data.
The candidate ordered 3/6 held-out alternatives correctly versus 2/6 for its matched
control. Pair-margin loss fell from 1.55931 to 1.55086. Ordinary validation capped-MSE
was74,292.61 versus 74,076.24 for control and73,951.55 initially: a small regression,
within the predeclared1% limit. This single additional correctly ordered pair is
not a general tactical-strength claim. Four learning/partition tests passed1.39s.

Next gate and budget, declared before runtime probes: freeze both models in exact
v1.41 runtime copies, changing only the value model and residual-enable configuration.
Run strict read-only package checks and one1s probe per model and v1.41 on the union
of exposed stable-error/mate-transition roots from confirmation01 and cycles03–05.
Require legal/restored positions, candidate repeats no more recorded mistakes than
control or v1.41, and candidate node throughput at least70% of v1.41 and80% of the
matched control. Do not claim a changed move is necessarily correct.

If that gate passes, predeclare 24 ordinary development games at 120+0.5:8 against
the matched score-only model,8 against v1.41, and4 each at nominal2400/2600. Use
the exposed elite openingsoffset0, both colours, at most 2 simultaneous games;
then audit all rated own moves. No new fitting or checkpoint selection during the
screen. If the gate fails, publish the pilot's limitations and save the match budget.

Runtime gate passed on 36 exposed roots. v1.41 repeated 30 recorded mistakes and
agreed with the teacher's first choice on 2; score-only control repeated 11 and
agreed on 7; preference candidate repeated 10 and agreed on 9. Mean completed depth
was6.028,6.083 and6.028 respectively. Candidate visited19,486,720 nodes versus
21,790,720 for v1.41 and19,785,728 forcontrol, satisfying the predeclared throughput
limits. These roots include training and held-out-family examples; this is not
fresh generalisation evidence and changed choices are not automatically good.

Both frozen models passed strict read-only inference, init17.57s/control and
17.51s/candidate, peak230.1MB/230.5MB and maximum measured search calls3.442s/3.485s.
Their exported values matched actual incremental compiled evaluation on 68 boards
to within 0.5cp. Original starting weights ordered 1/6 held-out pairs correctly,
score-only training2/6 and preference training3/6. Four tests passed for gradients,
mixed-perspective signs, clipping and opening-family partitioning.

Archived builds: v1.45 is the matched score-only control, ZIP SHA256
`8efafa6335d6ae120a3c8414ea397f62c9ef0602b849b58b5895f9929df49f9d`;
v1.46 is the preference candidate, ZIP SHA256
`61b6208f066dd134e9a927a2fdb4681b15cb252188b4eb8b2456b388a8390a15`.
Only their value.npz differs from each other; other runtime files match. v1.41
remains selected while the fixed24-game comparison/rated screen runs.
