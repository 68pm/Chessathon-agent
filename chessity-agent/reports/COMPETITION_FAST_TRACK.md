# Competition-first development â€” 7 September 2026

Deadline: 11 September. Competition games run hourly between 08:00 and 22:00;
the user wants improvements available for upload before the final deadline.
Dashboard: https://aichessathon.com/dashboard (authenticated access verified). Prioritize its
latest 2â€“3 matches, which the user says use more recent bots. Older matches used
older versions. Record the version as unknown unless metadata or the user verifies
it; never pool historical results as current-agent evidence. Download/read access
is authorized; replacing the live competition upload is not.

Latest user instruction overrides the long-term consistency programme: build the
strongest practical competition upload quickly. The 256-game study is abandoned
as interrupted, with zero completed games. Do not restart it or prepare a new
large qualification attempt. Preserve its evidence and all frozen agents.

The initial four diagnostic games of selected v1.41 at 120+0.5 are complete:
0W/0D/2L at nominal2400 and1W/0D/1L at nominal2600. Audits are complete; do not
repeat them. The latest actual competition rounds54â€“56 were also saved and
analysed (2W/1D/0L); three middlegame errors in the wins are now development
targets. v1.41 remains selected. Cycles09/10 failed their tactical gates. A deeper
trace preferred the correct defence but the root could not finish that depth
within12 seconds. Cycle11's exact evaluation cache gained only4.6%, below its
speed gate. Cycle12's exact passed-pawn masks also missed their gate. Cycle13's
sufficient legal-pawn proof passed exact-work and speed checks, followed by the
read-only package check. Its completed pair scored 0W/1D/1L versus41. Completed
failed experiments must not be repeated unchanged or treated as uploaded models.

For provenance, the completed four-game diagnostic used one colour pair
against nominal2400 and another against nominal2600. Reuse balanced starting
entries1 and2 (zero-based) from consistency-01/starts.json; entry0 belonged to the
unfinished games and is not reused here. Convert their recorded legal opening
lines in the common fixed-match runner. Positions were picked before outcomes;
retain all four results. At most two games run simultaneously. Then independently
audit legality, clocks, outcomes and source, analyse every rated own move using
the existing20k screening and80k/320k verification, and classify the first warning
separately from the terminal phase. This is a small development check, not Elo
certification or an automatic opponent-retirement gate.

While games run, inspect source and existing audited errors without competing
heavy training or teacher workloads. Engineering is first priority: improve useful
threat calculation, move ordering or conversion using a measured mechanism.
Learning is second: no new epochs or residual blend unless it addresses a diagnosed
failure. Data is third: reuse existing verified errors and alternatives before
collecting more games. Keep the current champion unchanged while testing variants.

Prefer a bounded tactical/position gate and2â€“4 preliminary comparison games to
reject weak ideas quickly. A promising potential competition upload can receive
an8â€“12-game fresh practical check, subject to the user's deadline. Report the small
sample honestly; this supersedes requiring a large long-term confidence study for
every competition choice. Require legal moves, real-clock and strict read-only
runtime checks. Do not promote merely because a version number is newer or a
training loss fell. Keep the previous verified ZIP available.

The existing2400->2800 and2600->3000 replacement mappings remain historical
preferences; do not spend this competition preparation on long ladder certification.
No automatic broad downloads, overnight validation, paid compute, competition
upload or write-access grants. Publish justified versions and the best downloadable
agent. Long jobs use a hidden service-owned Windows Task Scheduler launch and
actual process/timestamp checks; preserve interruptions without invented outcomes.

Completed practical pair: **0 wins, 1 draw, 1 loss against v1.41**,120+0.5. All source, legal-move, clock and outcome audits passed; candidate runtime failures=0. Selected download: **v1.41**. This follows the declared practical rule and does not establish an Elo gain or stable superiority. v1.41 is retained.

Cycle14 traced the quiet-defence and promotion failures. Cycle15's contextual
passed-pawn correction passed its 14-position and read-only gates. The user now
requests a ten-game comparison: two games each versus v1.41, v1.47, v1.48 and the
nominal2400/2600 bots. The fixed recipe is `configs/competition-queen-pawn-battery.json`.
Complete all games, then phase/mistake audits; no teacher workloads during games.
Do not expand this into a long consistency check or change the selected upload
merely because a candidate is newer.

That ten-game comparison is complete: see [results](COMPETITION_TEN_GAME_REVIEW.md).
The queen-pawn candidate remains experimental after0W/0D/2L against41 and two
startup failures. Its2600 win was an opponent flag. User-requested mistake replay
completed separately, with actual weight updates and three rounds. Its held-out
gate failed, so v1.41 stays selected; see [cycle16](IMPROVEMENT_CYCLE_16.md). Claude was explicitly
cancelled. Analyse only recent-build match histories, with provenance recorded.
