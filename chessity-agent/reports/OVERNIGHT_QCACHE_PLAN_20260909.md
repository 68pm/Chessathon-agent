# Second pass, engine priority: exact tactical-search reuse

Written before implementation/measurements. The first pass rejected geometry,
hash/scout, shallow check budgeting and the new value fit. New public rounds73–75
have been imported and all174 own decisions reviewed. Leader-game review runs
serially first; this next engine trial must wait for that teacher job to exit.

The selected53 search stores only ordinary search nodes in its transposition
table. Its near-queen checking branches can use most of a one-second move without
finishing depth2. Test reusing completed quiescence results, preserving the exact
tactical limits and all legal alternatives. This mechanism was not present in
the previous static-value cache, null-move or root-scout experiments.

The cache identity must include board/legalEP, halfmove clock, full history
context, extension credits, quiet attacker and credits, signed depth and qdepth.
Use a distinct negative table-depth tag, normalise mate distances, and reuse only
exact results or bounds satisfying the current window. Do not replace ordinary
search entries with quiescence entries. Terminal precedence and interrupted
search restoration remain unchanged. Model, policy and time manager remain53.

Correctness first: independent bound/mate/context/priority tests, an extracted
search control-flow test for repetition/mate/abort precedence, and balanced
production fixed-depth comparisons on22 roots (16previouscontrols plus six
new own-game weaknesses). Every fixed-depth2 probe must finish, with identical
scores/depths across builds. Different equal-score ties are permitted. Keep all
failed probes; do not rerun a timed-out pair until it happens to pass.

Two production workers import serially, each under90s, then stay resident with
one search at a time. ABBA per root for depth2 (12s/2M hard caps) and1s moves.
Efficiency gate: total fixed-depth CPU speedup>=1.10 and no lower mean clock
depth, in addition to completion/score parity. Report median and aggregate
results, node counts and wall times, including contrary results.

Only a passing efficiency trial receives80k/320k full-history teacher review of
clock choices, after student workers exit. Require non-increasing mean finite
regret at both budgets and no increased major-error/mate-loss counts per root.
An exact optimisation need not change a move to qualify. Any semantic mismatch
rejects it. Then strict read-only validation and the previously fixed four-game
incumbent comparison are required before a provisional promotion or rated ascent.
No claim of faster or stronger play is made until measured.
