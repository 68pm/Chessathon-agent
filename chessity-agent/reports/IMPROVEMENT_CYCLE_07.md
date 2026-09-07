# Cycle 07 — calibrate how much the learned evaluator can override the baseline

Written before calibration probes. v1.46's completed comparisons scored2W/3D/3L
against its score-only control and1W/2D/5L against v1.41. Its fixed rated schedule
continues; do not alter it. A separate bounded audit of the8 completed incumbent
comparison games found6 stable>=200cp errors in377 own moves. One chose the wrong
rook for Rb1; another ignored a bishop-trapping pawn threat with96 seconds left.
The dataset parser correctly converts annotation scores to side-to-move perspective;
there is no evidence of a label-sign bug. Better old-data MSE did not predict play.

Hypothesis: using the neural correction at full scale lets imperfect static values
override reliable baseline distinctions. The current residual can contribute±500cp.
Test one fixed quarter-weight setting, limiting its contribution to±125cp, keeping
the trained v1.46 weights, search, clocks and opening preferences unchanged. This
is a calibration experiment, not another fit or a search over many blend values.

Probe budget: one1s probe per root on all6 stable comparison errors for barev1.41,
full-weightv1.46 and quarter-weightv1.46. No old-model parameters or files change.
Then independently evaluate every distinct selected move at80k/320k teacher nodes,
with actual history and full legal root alternatives. Reuse the original unbounded
root-best/played analyses when they exactly match. At most18 distinct moves and
7.2M requested additional teacher nodes. Preserve all unstable/mate cases.

Unlike mere first-choice agreement or changed-move counts, compare actual finite
teacher regret for the selected moves. Clip regret to1000cp for averaging; require
at least4 roots with finite scores for all three variants. Quarter weight must
strictly reduce average regret versus full weight at both budgets and be no worse
than barev1.41 at either budget. It must not add a verified forced-mate loss. Any
unresolved selected-move score or fewer than4 comparable roots fails the gate.
Finite centipawn results remain separate at each budget; do not hide magnitude
changes by averaging budgets together. Mixed finite/mate or changing mate signs
are unresolved. Stable mate results are reported separately from centipawn means.
These deliberately selected failure positions are development data, not evidence
of general strength. Do not weaken the gate or try further blends after seeing it.

Only a passing quarter-weight build receives a strict read-only check and a new
fixed16-game development screen (8 vs v1.41,4 each nominal2400/2600 at120+0.5,
exposed elite openingsoffset0, at most2 games), queued after cycle06 completes.
Audit its rated decisions before any further change. Promotion still needs fresh
independent comparison against v1.41. If calibration fails, preserve the result and
choose a different mechanism from the diagnosed errors rather than repeating it.

The fixed diagnostic passed. All six roots had finite selected-move scores at both
teacher budgets, with no unresolved or mate-scored cases. Mean regret in centipawns
at80k/320k was279.0/398.17 for v1.41,289.0/404.83 for full-weight v1.46, and
238.0/355.0 for quarter weight. Reusing identical analyses limited new work to
800,000 requested teacher nodes. Quarter weight improved one rook move relative to
both controls and avoided another full-weight mistake; it still repeated four of
the six original errors. In particular, the bishop-trapping threat remained unsolved.
This small selected sample supports the planned match test, not a general gain.
One-second probes ran sequentially on the shared development host, alongside the
existing rated screen. Their completed depth and node counts are diagnostic only.

Frozen v1.47, compiled-paired-quarter-v1, differs from v1.46 only in runtime.json:
the residual contribution is multiplied by0.25. No weights were retrained, and no
other experimental search/table changes were added. ZIP SHA256
`bf1e1690c44cfb89a66c6e04f40303f7ab88f3b425e8dd9e0093f3f42ef674b7`;
364,838 bytes compressed and420,120 bytes uncompressed. Strict read-only inference
passed, including actual table choices, two120000ms clock calls, no subprocess or
network, and all file mutations blocked. Initialization19.506s, peak230.43MB,
maximum measured search call3.484s. v1.41 remains the recommended upload.

The predeclared16-game screen is queued behind the unchanged cycle06 controller,
with its completed rated audit required before cycle07 begins. Its own rated audit
follows the games. No fitting or checkpoint selection occurs during either screen.


Interruption disclosure: at14:31UTC the original controller and all chess worker
processes were absent, although the saved status still said running. The cause is
unconfirmed. Game2 had completed as a draw; its full record was independently
audited and retained. Game1's latest snapshot was at ply37, last updated13:37:49UTC;
game3 may have been initializing after game2 completed. No result is assigned to
unfinished attempts. The controller, log, report and snapshots were preserved in
interruption-20260907T1432. Frozen runtime/harness/teacher hashes and the original
schedule were rechecked before resuming the remaining games, with a hidden detached
controller. Unfinished games restart from their declared setup; completed game2
is not replayed. This interrupted development screen cannot serve as fresh final
confirmation. No thresholds, source files, weights or completed scores changed.
