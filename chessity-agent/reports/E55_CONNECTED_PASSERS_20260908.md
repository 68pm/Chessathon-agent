# Target the missed35.c5 conversion in the draw

Independent80k/320k review:35.c5 retains+282/+337cp, actual35.Bc1 gives-4/+6.
The queenless position contains White passers b6,c4,d4. c5 makes a pawn chain
d4-c5-b6; Bc1 does not. Current53 counts advancement of each passed pawn but
has no term for pawn support of another passer. This is a separate hypothesis
from the bishop–queen search trial and starts from unchanged53.

Only in queenless positions, add2*relative_rank_squared to the endgame component
for a passed pawn actually defended by a friendly pawn. Taper with the existing
material phase. Require no enemy pawn ahead on its or adjacent files. No change
to search, king-target terms, neural weights or the old isolated passer bonus.
This is a small connected-passer term, not a blanket premium for aggression.

Use the same frozen17 exposed roots as the battery trial and reuse its completed
exact53 baseline (record its hash). Run4 oracle/restoration/mirror/scope tests,
then one1s prototype probe per root with90s init and1.25s call bound. Independent
80k/320k choice review, maximum13.6M requested nodes with identical-choice reuse.
Same serial hiddenNormal4 and2048MiBdisk/768MiBRAM launch guards. No retry or
threshold adjustment after results.

Acceptance requires35.c5-case regret<=50cp at BOTH budgets, at least one100cp
repair, fewer paired200cp mistakes and lower mean regret at both budgets, no
new paired200cp or mate-loss error, legal/restored/on-time probes. Other draw
cases remain visible. No Elo inference from exposed development positions.
Only a passing candidate advances to read-only and a small53 pair before the
authorized2400/2600 rematch;2800 requires a played2600 win. No long study.
