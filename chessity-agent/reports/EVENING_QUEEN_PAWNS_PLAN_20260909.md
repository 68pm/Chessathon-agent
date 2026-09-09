# Queen-versus-pawns value correction on exactv1.56

The king-pressure-only integration fixed45Ke4 but regressed43Nxe5 and an older
move15, so it is rejected. Do not combine it into this candidate. Currentv1.56
still gives a seventh-rank passed pawn a180cp endgame bonus even when facing a
queen with no friendly queen. The earlier successful queen-aware evaluator
reduced that specific bonus; transfer only that original correction.

Detect queens in the existing first material pass. For phase<=8, if a passed
pawn's enemy has a queen and its own side has none, use2*r*r rather than5*r*r
for the endgame passed-pawn bonus. All ordinary queenless and balanced-queen
positions retain the original value. No search, ordering, model, king-pressure
or rejected LMR/repetition changes. Verify against independent passed-pawn and
material-phase calculations, including colour symmetry and unchanged scope.

Use the unchanged12root evening ABBA1second protocol and independent two-budget
teacher gate (2.56M/10.24M at23...Re6). Require no new major/mate regression and
non-increasing mean regret at both budgets, with>=10% reduction at one. This
addresses a concrete evaluator error rather than fitting on a self-chosen PV.
Preserve other existing independently labelled descendants for later learning.
No new broad data is needed. Match openings are still unplayed. Only a tactical
pass permits the same strict>=3/4 versus56 and short rated/read-only gates.
