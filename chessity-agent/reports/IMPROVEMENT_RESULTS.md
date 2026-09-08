# chessity-agent v1.53: provisional practical update

**Recommended upload: v1.53**, with v1.52 preserved as fallback. The engine now
follows bounded sequences of forcing checks when the queen approaches the enemy
king. The tactical gate and strict read-only validation passed. Its two-game
120s + 0.5s comparison against v1.52 scored **1 win, 0 draws, 1 loss**.
Both games ended by checkmate, with no clock, startup, crash or illegal-move
failure on either side. Both Black sides won: one opening pair does not prove
overall superiority or a calibrated Elo. This is a provisional recommendation.

Only engine/compiled_core.py changed from v1.52. Trained policy weights, optional
Alien preparation, endgame tables, time management and startup code are unchanged.
There is no new neural fit. The separate exchange-ending evaluation error remains.

| Check | Result |
|---|---|
| Diagnosed mate-in-six positions | Both found with bounded quiet checks |
| Original played mistakes repeated in 21 clock probes | 12 to 11 |
| Mean teacher regret at 80k / 320k nodes | 258.71 / 276.67 to 236.86 / 255.76 cp |
| New stable 200cp errors or mate losses in the tactical gate | None |
| Read-only initialization | 77.155 seconds |
| Legal read-only move calls | 2 |
| Peak read-only memory | 224.73 MiB |
| Comparison with v1.52 | 1 win, 0 draws, 1 loss |

Every move, source, outcome and both clocks were audited. Offline teacher review
screened all 119 candidate moves and verified suspicious choices
at 80k and 320k nodes. It found 4 finite errors of at least
200cp at both budgets and retained 21 mate-scored rows separately.
It requested 33,060,000 nodes within the predeclared
99,960,000 maximum. These are development observations,
not accepted neural-training labels or a fresh rating estimate.

| Game | First verified warning | Terminal stage |
|---|---|---|
| White loss | 26. Rd4 (middlegame); teacher alternative h3 | middlegame |
| Black win | 16... Qg5 (middlegame); teacher alternative Qg4 | endgame |

Stage labels follow the saved material-based definition; move number alone does
not determine the reported phase.

The first review wrapper failed before teacher launch because it did not create
its output directory. Its source, plan and logs are retained. A corrected wrapper
completed the original review; no games or teacher samples were repeated.

Engine improvements remain first priority. The next diagnosis should separate
missed opponent continuations from misvalued exchanges. Useful learning requires
independent values for both candidate and stronger opponent continuations and a
compatible network objective. The reviewed games provide the targeted data;
broader game downloads and unchanged training epochs are not justified yet.

The highest opponent this exact build has beaten is **Chessity v1.52**, whose
Elo is uncalibrated. Its subsequent rated screen is recorded below.
No older version's wins are attributed to it. The long consistency study remains
cancelled. Submitted inference is read-only, without network or subprocesses;
no live competition upload or repository permission changes were made.

[Tactical evidence](NEAR_QUEEN_CHECKS_RESULTS_20260908.md) ·
[Original practical rules](NEAR_QUEEN_CHECKS_PRACTICAL_20260908.md) ·
[All practical evidence](evidence/near-queen-practical-20260908/manifest.json)


## First rated screen: 8 September, E90

**Nominal2400: 0 wins, 1 draw, 1 loss. Nominal2600: 0 wins, 0 draws, 2 losses.**
One threefold draw and three checkmate losses; no failures on either side.
No rated opponent was defeated in that first screen. Its recommendation remains
provisional; neither higher overall strength nor a calibrated Elo is established.

Review of160 own moves found7 finite paired200cp errors and17 mate-scored rows.
The first loss developed in the opening; the other two first warnings were in
the middlegame. Next work examines defensive continuations before another fit.

[Full rated results and diagnosis](NEAR_QUEEN_RATED_RESULTS_20260908.md).

## Latest requested screen: E55

**2400 1W0D1L; 2600 0W1D1L**. Failures on either side: 0. Highest nominal checkmate win in this screen: 2400. The same v1.53 code and weights were used.

Cumulative rated results for exact v1.53: **2400 1W1D2L; 2600 0W1D3L**. Different small opening screens do not establish calibrated Elo or consistent strength.

[Latest full results](COMPETITION_CONDITIONAL_RATED_RESULTS_20260908.md) · [Defensive/rook targets](COMPETITION_COUNTERFACTUALS_RESULTS_20260908.md).
