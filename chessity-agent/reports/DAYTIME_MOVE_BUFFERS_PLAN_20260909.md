# Reuse per-ply move and ordering arrays

The selected engine allocates a 256-entry move array whenever search generates
moves and another array whenever it scores their order. Test reusing separate
move and score arrays at each search ply. This targets repeated allocation work;
the earlier piece-square table lookup was slower and is not included.

Start from exact selected v1.55. Keep the original generator and ordering helper
for legality checks, root setup and reference comparisons. The buffered helpers
use the exact same move rules and scores, with checked writes and a distinct
512-entry row per ply. At 100 plies, the two int64 arrays add 819,200 bytes. A
descendant cannot overwrite its parent's array. Existing maximum-ply, restoration,
interrupt, repetition, value and policy handling remain unchanged.

Check 880 deterministic legal positions and mirrors, diagnostic roots, special
moves, separate-ply storage and safe undersized-buffer failures. Require matching
generated order and move scores plus state and function isolation. Then use the
existing twelve-root, 96-call warmed ABBA protocol: fixed 250k nodes/12s maximum
and one-second searches. Fixed move, score, depth and node results must match
exactly. Require >=5% aggregate and median CPU gain and no mean depth reduction.

Only an efficiency pass proceeds to independent 80k/320k clock-choice review.
Only both gates passing permit short 120+0.5 games with every outcome reviewed.
Keep v1.55 selected unless practical evidence justifies a successor. No failed
table, mate, history, cache or value experiment is bundled. All work remains
serial, with capacity, STOP, owned-process and daytime deadline guards.
