# Quiet pawn-threat search experiment

On the strongest retained engine, stop applying late-move reduction to a legal
quiet pawn move that attacks an enemy piece/pawn from its new square, or reaches
the seventh rank. These are forcing threats without necessarily being checks or
captures. This guards replies as well as our own moves. Keep capture, quiet and
sacrifice ordering unchanged; do not add pruning or force any opening move.
Use the repetition optimisation only if its predeclared exactness/speed gate
passes; otherwise use unmodified selectedv1.56 as the parent.

Before play, compare 12 declared tactical roots in warmed ABBA order at1second
per search, with full original move history and cleared transposition tables.
Seven roots are recent diagnosed public-game errors (including23...Re6); five
are older mixed regression positions selected by fixed order before probes.
These are development positions, not independent strength evidence. Review
choices independently at80k/320k Stockfish nodes, except the horizon-sensitive
23...Re6 position, which uses2.56M/10.24M. No root-label copying to descendants.
Require no new verified200cp mistakes or forced-mate losses; mean finite regret
must not increase at either budget and must decrease at least10% at one budget.
The ratio concerns sampled move quality, not playing Elo. Correctness, legal
moves, unchanged board/history, deadlines and frozen sources must all pass.

Then require read-only validation and the predeclared evening practical gate:
at least3/4 against exactv1.56 on reserved B12/D48 openings, at least1/2 against
nominal2400 and0.5/2 against nominal2600 on D65, all colours reversed and every
game reviewed. Stop early if qualification becomes impossible. A clean2600win
with pair score>=1 permits the2800 pair. Keep v1.56 and version number unchanged
if any required gate fails. Do not tune against the match gate after exposure;
reserve different openings for any later candidate trained on those games.
