# Exact repetition-query cost experiment on selectedv1.56

Normal legal chess has no two-ply return to an identical position. Threefold
repetition therefore needs at least eight reversible plies and nine recorded
positions. The engine contains no null-move search. For shorter histories/halfmoves,
return false immediately. Otherwise count the current key once, scan possible
same-side previous keys starting four plies back, and stop when three matches are
found. Include the same irreversible/draw-clock boundary as the original scan.
Do not change hash generation, history construction, castling/EP keys, TT context,
draw precedence over checkmate, search scores/order or any trained weights.

Check against the original full scan and python-chess on actual legal histories,
including repeated knight/king cycles, resets, castling/EP and full-history slices.
Arbitrary colliding synthetic hash keys are not a proof of a legal repeated board;
both versions still have the same inherent Zobrist collision assumption. Test
counting parity over complete legal prefixes and exhaustive short legal cycles.
Check source change scope. No null-move search may be added without revisiting
the minimum-cycle shortcut.

Use the existing frozen warmed ABBA harness with new sources/bounds only:
12 roots including recent Petrov/Catalan/Closed Sicilian errors and longer
reversible histories.250000-node fixed-work and1-second clock probes, four runs
per root/regime. Require exact move/score/depth/node parity, all correctness tests,
aggregate and median CPU speedup>=1.05, no lower mean1-second depth. Otherwise
reject and retain v1.56. A speed pass still needs teacher review and the stricter
short practical promotion gate in the evening journal; it is not itself strength.
