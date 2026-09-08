# Cycle38: legal quiet-check opportunities in king evaluation

Predeclared before measurements on8September2026. Unchanged v1.53 is the control.
The recent descendant review found both accurately valued exposed kings and badly
valued stronger opponent continuations. Missing pawn cover alone does not explain
the difference. This pilot adds one general measure of available forcing moves.

For a side that still has a queen, count each knight/bishop/rook/queen once if it
has a legal quiet move that directly checks the enemy king and lands on a square
not pseudo-attacked by the enemy. Values are40/40/60/80cp per piece, capped240cp
per side. Add White minus Black opportunities to the existing tapered evaluation.
The hypothetical move must leave its own king safe. Blocked rays, absolute pins,
destination occupancy and enemy attacks are respected. Discovered checks and
checks on enemy-controlled squares are deliberately outside this conservative
feature. A queenless side receives zero. No pawn-file penalty, tuned square/FEN
rule, new weights, search-depth/clock change or failed root-PVS combination.

These fixed engineering coefficients are a hypothesis, not fitted parameters.
No coefficient sweep or adjustment after seeing outcomes. Search and all other
core functions must be AST-identical to v1.53. The new helper restores the board.

One fresh production worker per build, serial, with90s initialization and360s
owned-process bound. Prototype checks the feature against an independent
python-chess legal-move oracle on120 seeded positions plus23 saved endpoints,
both sides and reflected positions. Preserve the two established mate-in-six
proofs, terminal precedence and512-node interruption/restoration check.

Both workers evaluate the23 actual-history endpoints using qsearch100k nodes/2s
each, NULL on interruption, and replay the existing21 regression roots plus all
three cycle37 loss-transition roots once each at1s with identical fresh tables,
real history and policy disabled. Every attempt records nodes/wall/state before
checking limits; no new JIT signatures may appear during measured search calls.
All labels and teacher scores are the existing independent80k/320k values.

Cheap gate: all correctness/resource checks pass; all endpoint probes complete;
mean endpoint absolute error decreases at BOTH teacher budgets; no endpoint
previously below200cp at both becomes at least200cp wrong at both; fewer original
played-mistake repeats over24 clock probes, and at least one of the three recent
loss-transition choices changes. This is exposed development data, not holdout.

Only if that passes, review all48 clock choices at80k/320k with the existing cache
and references, at most19.2M newly requested nodes. Require lower mean regret at
BOTH budgets, no new paired200cp mistake or mate loss, and at least one of the
three recent roots improved by100cp at BOTH budgets relative to control. The
earlier repaired Bxf2+ root must remain within50cp at both budgets. No games or
automatic release here; a pass permits read-only validation and a small practical
comparison. A failure stops this hypothesis without an unchanged retry.

All three priorities: engine evaluation first; useful learning second requires
independent counterfactual descendants and a representable objective, and is not
claimed from this handwritten change; targeted existing23 endpoints/24 roots
third, with no broad download or new neural fit. No calibrated Elo claim.

Require2048MiB disk and768MiB physical RAM before every heavy process, including
the teacher. Hidden SystemPowerShell NormalPriority4 from launch, no overlapping
heavy work, STOP flags and20minute maximum capacity waits. Preserve all attempts,
frozen source/config/data, archives and selected v1.53 bytes.
