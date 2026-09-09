# Compact learned position-value head

Four engine experiments have completed without passing promotion gates. Retain
exactv1.56. Its hand-written piece-square scores are a concrete low-cost learning
target: fit an original linear position head with separate middlegame/endgame
weights, naturally colour symmetric. This is768 trainable weights, not a new
large neural network. It evaluates searched positions, not just root move policy.

Reuse the13386 independently labelled rows of curriculum-value02, including
both actual colours, recent quiet descendants and GM positions. Preserve that
dataset's1200 broad development rows, deduplication and all reserved full-game
exclusions. Do not copy root action rewards onto leaf positions. No downloads.
Fit residual cp targets clipped to[-500,500], with no intercept. Per-row training
weights: broad1, recent4, GM2. Ridge penalties10/100/1000, coefficient cap80cp,
and candidate blends0.25/0.5/1 are the complete predeclared grid. Apply a250cp
output cap in both training evaluation and eventual runtime. Select exactly one
grid result by broad development capped MSE; never choose again after colour tests.

Require at least5% lower broad development capped MSE, non-increasing errors in
both positive and negative correction cohorts, and non-increasing recent/GM MAE.
Then test the existing exposed White/Black positions: each colour needs at least
6eligible positions, non-increasing MAE and no increase in>=200cp value errors.
Only after passing, independently label the three already reserved, unused whole
Italian games. Freeze weights before those labels; verify full-game exact/mirror
exclusion. Apply the same colour gates on these fresh positions. Preserve all
failed results without hyperparameter selection on the reserved positions.

Only a full value pass permits isolated runtime integration, independent dense
versus compiled scoring tests, the12root equal-clock tactical gate and the strict
evening read-only/match gates. Do not package merely because a fitting loss falls.
This is a bounded architecture alternative to the earlier failed16unit fits.
All earlier sources/results stay immutable. Raw GM histories remain local only.
