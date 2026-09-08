# Cycle21: one quiet-check layer at the search boundary

Declared before measurement. Cycle20 aspiration failed its cheap gate: mean
depth rose only0.206 ply, while repeated errors increased28 to29. Both builds
still chose37Kf1 at depth7 and16...f4 at depth6. Do not retry its timing or blend
the rejected aspiration code into this prototype. v1.51 remains selected.

Engine need: useful threat recognition, not depth alone. Current quiescence
search explores captures/promotions outside check and all evasions in check.
It excludes non-capturing checks at quiet leaves. Test whether ONE initial
quiet-check layer helps recognize forcing threats before evaluating a position
as quiet. This is a hypothesis about the new king-defence error, not a proven
explanation of the full loss. Use the selected51 core and driver; only the core's
quiescence move expansion changes.

At depth<=0, not in check, qdepth==0, generate the ordinary moves but discard
non-captures that neither promote nor check. Existing capture/en-passant and
promotion handling remains. All evasions remain available when checked. At later
quiet leaves use the original captures/promotions-only search. Stand-pat,
terminal/draw rules, maximum ply, check evasions and clock/node stops remain.
No new check extension, aspiration, reductions, evaluation or trained weights.

Learning need: preserve weights while isolating this tactical search change.
The previous replay-target capacity mismatch remains unresolved; do not fit
another epoch or increase the blend. Search-generated leaf examples may be
useful for a later capacity-compatible value objective, after this hypothesis
is measured. Data need: reuse all17 frozen cycle20 roots, including all three
new stable errors; no new broad download or selective replacement of positions.

## Fixed checks and gate

Ten focused checks cover non-capturing mate at the first leaf, the one-layer
limit, quiet check evasions, stalemate, mate precedence over draw counters,
non-capture promotions, interrupted castling/en-passant/promotion state, and
real repetition history. Compile outside test search deadlines. On test failure,
preserve evidence and diagnose the concrete implementation/fixture failure.

Then two fresh processes, baseline51 followed by prototype21, each on all17
roots for1second with policy disabled equally and full history/state restored.
Also probe the three new roots at250k nodes with an8second safety cap in each
process; safety-capped cases are reported rather than claimed as fixed-node parity.
Record initialization<=90s, legal/restored/depth>=1 and outer wall time<=1.25s
for clock probes; fixed-node probes must stay<=8.25s. Preserve every result.
The child has a300second hard timeout, terminated as its owned process tree
on Windows. Require both>=2048MiB disk and>=768MiB RAM before heavy work, bounded
20minute guard wait, no other heavy work or timed games. Respect both STOP flags.

Cheap gate requires strictly fewer original-error repeats in the17 clock probes,
and the new king-defence root must avoid37Kf1 in at least one of its two probes.
If it fails, stop; no threshold changes or unchanged timing retries. If it passes,
review all20 choices per build at80k/320k with original labels and cached moves
where possible (at most16million new nodes before cache). Require lower mean
capped regret at BOTH budgets on the17 clock roots, no added stable200cp paired
error or mate loss in either probe mode, and at least one king-defence choice
within50cp of the teacher at both budgets. Keep the three extra fixed-node
diagnostics separate from the17-position mean.

A pass permits packaging and strict read-only validation, then exactly two
120+0.5 games versus51 from the next unused prepared opening index6, both colours.
Require>=50% score and no candidate operational failure before considering a
small follow-up. No automatic release, estimated Elo or long consistency study.
