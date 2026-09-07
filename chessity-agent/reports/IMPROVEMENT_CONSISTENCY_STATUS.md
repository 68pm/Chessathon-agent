# Independent consistency checks in progress

The user requested the full checks immediately. The frozen recommended v1.41
started at 2026-09-07T16:46:43.361270+00:00 with **256 fixed games at 120s + 0.5s**:
two 64-game blocks against nominal2400 and two against nominal2600.
At most two games run simultaneously; no training or teacher analysis runs beside
them. This page records the start, not a live scoreboard or completed result.

Preparation selected64 distinct ECO groups from the existing CC0 opening
dictionary after excluding143 previously exposed
groups. It checked87 candidates with fixed20k/80k-node
balance tests. The same64 groups are used at both strengths, in both colours;
the32 groups in the second block differ from those in the first. Related opening
theory may have occurred in historic training. Group independence and stable host
conditions remain statistical assumptions.

Global attempts1 and2 were registered before games. Both blocks must pass the
predeclared outright-win lower-bound test and independent source/clock/outcome/
freshness audit. Every loss, draw and runtime failure is retained. No opponent
is removed during the running schedule. The final report will include W/D/L by
block and opponent, uncertainty bounds, and qualification status.

Eight harness tests passed. An initial preparation reader error involving a legacy
post-opening FEN plus full opening list was preserved and corrected before any
balance selection or candidate games. This was not a match interruption.

v1.41 remains the recommended upload. No new release was created. Estimated runtime
is8–14 hours, with the previous24 rated games averaging292.25 seconds per game.
This is an estimate, not a completion guarantee. Engine settings are not calibrated
human, FIDE or Chess.com ratings. [Predeclared protocol](IMPROVEMENT_CONSISTENCY_01.md).
