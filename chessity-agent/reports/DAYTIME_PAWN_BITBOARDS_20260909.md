# Exact scalar evaluation on v1.54

The defensive trace shows missed alternatives even without late-move reductions.
Removing reductions also usually reduces completed depth. Keep the existing
search and weights while testing a new way to make its evaluator cheaper.

Replace its three per-call heap arrays with two scalar pawn bitboards and scalar
bishop/material counts. Build the pawn masks during the existing first board
scan. Reuse verified file and forward-mask formulae for doubled, isolated and
passed pawns. Preserve all scores and rounding. This implementation has no
incremental board metadata, bitset attack replacement, quiet-check extension or
compiler repair from the earlier v1.53 pawn-mask experiment. That older failed
quality result remains unchanged. The comparator here is exact selected v1.54.

First test high-bit/file edge cases and exact evaluation on 712 positions and
their mirrors, both conversion settings, plus unchanged search ASTs. Then run
96 ABBA probes over eight diagnosed roots and four previous control positions:
250,000 nodes with a 12-second guard, and one-second search. Require exact
fixed-work moves/scores/depths/nodes, both startups below 90 seconds, aggregate
and median CPU speedup at least 1.05, and no loss of mean timed depth.

A speed pass only permits independent Stockfish review of all clock choices:
nonincreasing mean regret at both 80k/320k budgets, no increased major-error or
mate-loss counts. Only a quality pass permits read-only validation and short
matches against v1.54/v1.53 and nominal 2400/2600. No new release is justified by
a microbenchmark alone. All playing weights remain frozen, all games reviewed,
and 2800 remains conditional on a clean 2600 win. Honour serial CPU, capacity,
STOP and the daytime deadline. Preserve every consumed attempt.
