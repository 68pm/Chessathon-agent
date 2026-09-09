# Overnight third checkpoint: two reviewed games and guarded value evaluation

The selected upload remains **v1.53**. No new numbered release has qualified.
All54 numbered ZIPs and the latest download retain their exact bytes. The new
countercheck integration trial is pending and excluded from this checkpoint.

## Exact completed game results

The compiler-repaired control completed two120s+0.5s games against the nominal2400
Stockfish setting: **0 wins,1 draw,1 loss**, with no playing failures. White lost
by checkmate; Black drew by insufficient material. This build uses v1.53's search
logic and weights with repaired compiler signatures; it is **not the exact
selected v1.53 ZIP**. Higher settings were not unlocked by this pair.

All134 agent moves were reviewed:85 independently supported good moves and11
negative signals. The reviews contain5 opening,51 middlegame and78 endgame moves.
Both experimental reward-policy updates completed. Playing weights remained
frozen; those checkpoints are not selected uploads. A Windows path-length error
initially interrupted review after the saved loss. Recovery preserved that game
and reviewed it without replaying it, then played only the unplayed second game.

[Full two-game result](evidence/overnight-third-pass-20260909/games/n9-dev-2400/rated-prototype/results.json).

The first confident loss error was23.e4; both teacher budgets prefer Rf3 by181/202cp.
The later33.Qxf4 mistake occurred in an already badly losing position and had an
unstable alternative, so it received no invented best-move target. In the draw,
several middlegame choices gave away evaluated advantages. A draw itself is not
a bad-move label; the independently reviewed decisions are the learning targets.

**SAN correction:** the draw's move35 alternative is **Qd6**, not Bd6. Saved UCI
targets and the preparation's SAN already contained Qd6. The earlier frozen
pair-value prose is preserved with this explicit correction. The candidate's
inferior pawn capture was **Qxd4**, followed by White's quiet **Qb6** rook threat.

## Engine and learning measurements

| Completed experiment | Evidence | Decision |
|---|---|---|
| Matched defensive extension |88 timed probes; mean regret worsened at both teacher budgets | Rejected;4 increased major-error counts |
| Quiet-check geometry prefilter |19,122 legal moves checked; preserves all914 checks;1.0741 fixed-work CPU ratio | Below1.10 speed gate |
| Combined exact search optimizations |26 checks;176 probes;1.1394 CPU ratio | Timed mean depth fell4.4545 to4.3182 |
| Scalar pawn-mask evaluation |12 checks; exact fixed-work parity;1.5321 CPU ratio; timed depth4.3864 to4.5909 | Speed passed; separate move-quality gate failed |
| Guarded781-feature leaf integration |13 checks;104 timed probes; four100cp repairs | Two increased major-error counts; no release |

The pawn-mask optimization removes repeated small allocations and pawn scans
without changing evaluation constants. Its useful implementation remains available
for later candidates, but its measured speed alone did not justify promotion.

The D65 game pair produced32 independently analysed quiet descendants:31 eligible,
one excluded. The entire opening pair was held together as one source group.
Labels used80k and320k teacher searches at each endpoint, not copied root rewards.
The new labels requested9.2M teacher nodes. They are now exposed development data.

On31 new, nonoverlapping descendants, the frozen value model reduced overall MAE
from190.84 to169.79cp. Its26 middlegame examples improved214.92 to180.60cp, while
five endgames worsened65.60 to113.60cp. This is why the guarded runtime leaves
endings classical. The old failed value-fit decision remains unchanged; this
diagnosis is neither a new fit nor evidence of playing strength.

Guarded-leaf-02 integrates piece accumulators, castling rights, legal en-passant
and draw-clock features, with a half-strength residual capped at300cp. It repaired
four diagnosed roots, including Rf3 in the new loss and a king move in the draw.
Mean regret fell157.00/179.98 to135.67/155.88cp at the two teacher budgets, but
opening move9 and draw move35 had increased major-error counts. Startup was72.42s
versus48.86s for the matched control. It failed the declared quality gate.

The first guarded draft had already been rejected for an omitted fullmove cache
context. The corrected draft and all failures are preserved separately. A further
bounded continuation trace found Qb6, yet still valued the line too favourably;
the pending experiment tests defensive counterchecks and fixes root opening
scope. No pending result or candidate ZIP is presented as a release here.

## Retained upload and rating limits

Exact v1.53's latest E55 screen remains: nominal2400 **1W/0D/1L**, nominal2600
**0W/1D/1L**. Across its eight rated games:2400 **1W/1D/2L**,2600 **0W/1D/3L**.
Highest clean nominal opponent beaten by this exact upload: **2400 once**.
There is no2600 win or2800/3000 result for it, and no calibrated Elo estimate.
The two new compiler-control games must not be added to those totals.

[Selected read-only ZIP](../latest/chessity-agent.zip), SHA256:
`5747acec37da25ea79704e49d19e45bf23bd2af5842a14eaf66bf6ecf2791315`.
The latest imported competition sample remains separate because the uploaded
version was not verified. This checkpoint does not claim a fresh site rating.

The07:20BST report remains scheduled. Later completed evidence or a qualified
successor will be reported separately.
