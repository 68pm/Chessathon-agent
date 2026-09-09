# Reuse stored moves without reusing foreign-history scores

The five-position selected-release probe confirmed that v1.55 still misses Bxh7+
at both public round 78 positions, still chooses exf6 instead of Ng5, and misses
the quiet ...Kg7 defence in round 77. One and three seconds reached depths six
and seven. It already finds the leader's correct ...Kg7 conversion move. Prioritise
the four persistent own-game failures; do not teach it to replace an already good
choice merely because the opponent once blundered there.

Test one isolated ordering change on the preserved, unselected fast-legal parent:
when a position hash matches a transposition-table entry, let its stored move be
an ordering hint even if repetition context or halfmove clock differs. Keep the
existing context, halfmove, depth and bound guards on every cached score cutoff.
The move is still selected only from the generated moves and checked for legality.
No score, weight, root-policy, pruning formula or draw rule changes. The faster
legal-existence component is retained as development source, not treated as a
qualified release. Compare the new ordering directly against that exact parent.

Tests must demonstrate both sides of the boundary: foreign-history scores cannot
cut off, but a legal foreign-history hint is visited first under a two-node probe.
Include illegal hints, completed full-width score comparisons and AST isolation.

Use 19 exposed diagnostic roots: the prior twelve efficiency roots, the five
public turning points, and the two major errors against v1.55 in the new screen.
Warm both processes, search serially in ABBA order. Fixed-depth probes use depth
six with reductions disabled, a five-million-node cap and twelve seconds. Require
completion and exact scores at every root. Compute fixed-depth CPU ratios only
for roots with baseline mean CPU at least 0.05 seconds and 10000 nodes; require
at least eight such roots, 5% aggregate and median improvement, and nondecreasing
mean completed depth in the one-second probes with normal reductions restored.
All roots remain in correctness and tactical-quality analysis, even when too small
for meaningful timing. Preserve failures; do not change thresholds after results.

Only a passing measurement proceeds to independent two-budget teacher review of
timed choices, then a short comparison against selected v1.55, v1.53 and nominal
2400/2600, with conditional 2800. Do not promote from speed alone. Keep CPU-heavy
work serial, capacity and STOP checks, owned-process timeouts and daytime cutoff.
