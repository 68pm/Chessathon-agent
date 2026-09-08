# Practical follow-through for cycle29

The predeclared tactical gate passed: clock mistakes14/17 to8/17; all motivating
king, endgame and rook requirements satisfied; no new paired200cp errors or mate
losses. This permits the already declared package check and two-game comparison.
It is not proof of a game-strength gain. The selected upload remainsv1.51.

Copy the exact tested prototype to candidates/compiled-king-coordination-v1 and
build an internal deterministic ZIP without changing its code or weights. Verify
every candidate file and ZIP entry. Run the existing strict read-only validation
once at120000ms with two legal calls, initialization below90s and memory below2GB.
Only success permits both120+0.5 games against selected51, one of each color.

Use index6 of the previously prepared consistency-01/starts.json list, theB89
Sicilian Sozin/Sherbakov position after10...b6. This uses one existing opening;
it does not resume the cancelled consistency study. Preserve the prepared source
hash and parse its complete20-ply PGN, verifying its exact starting FEN. Both
agents receive the same start under the existing serial game harness.

Keep all scheduled outcomes, including both games after any first-game result.
No added games until a win. Qualification requires at least50%score with no
operational/clock failure for either side; an opponent failure cannot supply
playing-strength evidence. Audit every move, both clocks, exact sources and
results. Selection and any numbered release remain pending this review.

Run only this hidden Normal-priority controller. Require2048MiB disk/768MiB RAM
before validation, each game and each fresh agent launch; wait at most20minutes
for capacity. Respect STOP flags. No overlapping heavy teacher, training or
other JIT work. Freeze the wrapper, configurations, candidate, old harness
dependencies and gate. A failed attempt is preserved and not retried unchanged.
After completion, diagnose the first actual deterioration before more fitting.
