# Cycle 05 — reuse move-order hints without reusing unsafe scores

Written before implementation. v1.41 remains the incumbent. Cycle03's reduction
candidate v1.42 scored1W/5D/2L against it,2W/0D/2L at nominal2400 and1W/2D/1L at
nominal2600. All 16 games were replayed and frozen sources/clock accounting verified.
The2600 win is a real checkmate in game5, with White, following the exposed Ruy
Lopez opening setup. It is a development result, not a rating or consistency proof.
One victory does not outweigh the failed incumbent comparison for promotion.

The rated audit found5 stable >=200cp mistakes in 304 own decisions. Its successor
pilot accepted4 of 5 pairs, leaving a total of 8 verified pairs across the two recent
pilots. Retain them for targeted replay; this is still little evidence for another
broad fit. The table-only v1.43 experiment is already running independently.

Mechanism: compiled search currently discards a transposition entry's move hint
unless both its board key and repetition-history context match. A matching board's
move remains useful for ordering even with different history. Its score or bound
may be wrong in that new history and must remain guarded by exact context and
halfmove-clock agreement. The hint only prioritises an already generated move;
normal legality checks still apply. No new pruning, evaluation, weights or clock
settings are introduced. Freeze a copy of v1.41 changing only compiled_core.py;
do not mix v1.42 reductions or v1.43 table changes into this test.

Predeclared gates: poisoned-context/halfmove TT score tests, existing legality/
terminal checks, strict read-only package checks, and equal-depth score comparison
with v1.41 on the combined exposed v1.41/v1.42 audited errors. Use depth4 with a
30s ceiling per position; require every result to complete and scores to match.
Then run one1s probe per build on the same positions. Require no more repeated
recorded errors and no lower mean completed depth before any ordinary-game budget.
Move ties may differ. These diagnostics are not fresh chess-strength evidence.

If gates pass, queue8 paired development games against v1.41 and4 each against
nominal2400/2600,120+0.5, exposed elite openingsoffset0, after cycle04 finishes.
Then audit the 8 rated games. At most2 concurrent games; no teacher/training during
fresh confirmation. Do not extend the fixed schedule to chase a win. If a gate
fails, critique that result instead of launching matches or changing the threshold.
No promotion or neural learning is implied by a search-speed gain.

Gate passed:21 core tests in 24.22s, including poisoned context/halfmove scores and
an illegal stored hint; all 16 audited positions matched v1.41 at completed depth4.
At1s per position, repeated original choices fell from 14/16 to 13/16, mean completed
depth rose from 6.25 to 6.4375, and visited nodes rose from 7,560,192 to 9,053,184.
These are small shared-host diagnostics, not a strength claim. The initial direct
test supplied a signed Python context unlike runtime's uint64; the test was repaired
to use the actual runtime type. No runtime code was changed to accommodate it.

Frozen candidate compiled-transposition-hints-v1, ZIP SHA256
`cbb28be43fde9f4902f48e90caae05423bd00aa1e8dbf2634813032e3717aabb`.
It differs from frozen v1.41 only in engine/compiled_core.py. ZIP272,557 bytes,
327,984 bytes uncompressed. Strict read-only checks passed with two real clock
calls, actual elementary-table decisions, init20.95s, peak228.7MB and maximum
measured search call3.485s. No socket/subprocess or file mutations were permitted.
The fixed16-game development screen starts after the completed cycle04 review.

Completed result:2W/2D/4L versus v1.41,3W/1D/0L at nominal2400, and0W/0D/4L at
nominal2600. All 16 games passed independent source, legal-move, clock and outcome
audits with no runtime failures. The rated audit found7 stable >=200cp errors
in 476 own moves. No promotion: the good small2400 screen did not carry over to
the incumbent comparison or2600. Do not repeat this unchanged ordering experiment.
The next cycle tests a different learning signal with a matched score-only control.
