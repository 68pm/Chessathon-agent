# Faster terminal-position checks

The selected v1.55 search checks whether a legal move exists at quiet quiescence
nodes to distinguish ordinary positions from stalemate. Its helper allocates and
fills a complete pseudo-legal move list before trying the first legal move.

Test one isolated change: first inspect the king's eight adjacent squares. For
each possible ordinary king move, use the existing make, attack and unmake
functions. Return true on a legal move; otherwise run the original full-list
fallback unchanged. The helper answers only whether a move exists. It does not
choose, order or prune moves in the actual search. Castling, en passant, pawn
promotions, interpositions and pinned pieces still reach the original fallback
whenever the fast probe cannot establish a legal king move.

Do not change evaluation coefficients, weights, time control, hashing, move
generation, search ordering or rules. All temporary board and state mutations
must be restored. Compare the boolean result against python-chess and the exact
v1.55 helper across eight explicit rule/terminal cases and 600 deterministic
positions plus mirrors. Verify that every other function's AST is unchanged.

After the current public-game review controller exits, prepare fast-legal-01
against exact v1.55. Reuse the 12 declared diagnostic roots from the prior pawn
benchmark and the same warmed serial ABBA timing harness: 250000-node probes
with a 12s cap, and 1s clock probes. Require exact fixed-work move/score/depth/node
parity, at least 5% aggregate and median CPU gain, and nondecreasing mean clock
depth. These are exposed development measurements, not new strength evidence.

Only a successful efficiency gate proceeds to independent teacher review of its
clock choices and then the short practical match screen. No selection or upload
occurs from a microbenchmark alone. Preserve failed sources and the selected
ZIP; use current capacity/STOP checks and the daytime deadline.
