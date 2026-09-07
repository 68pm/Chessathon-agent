# Cycle 12: exact passed-pawn masks

Base: frozen v1.41 alone. Its evaluator scans every forward square on three
files for each pawn at every leaf. Replace those repeated nested scans with
precomputed geometric masks and two pawn-occupancy bitboards built during the
existing board pass. This preserves the definition and exact evaluation; no
search, move-order, cache, pruning, weight or scoring change is included.

Compare against the existing Python evaluator on1500 random legal positions
and explicit edge-file, blocked, doubled, backward and advanced pawn cases.
Then run the same bounded exact-work gate: all11 known errors,250k nodes each,
two passes in alternating build order. Require exact nodes, scores, depths and
moves, plus at least10% aggregate speedup. Never rerun a failed timing gate.
If passed, freeze and verify read-only operation, then play two colour-paired
120+0.5 games against41. No long independent consistency check or Elo claim.

Engine efficiency is first priority. Learning is deferred because evaluation
targets are intentionally unchanged; targeted existing errors suffice for the
measurement and no additional downloads or fitting are required.
