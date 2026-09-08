# Chessity v1.52: tactical improvements and a short practical screen

**Recommended upload: chessity-agent v1.52**, a provisional competition choice
under the small-test rule declared before its games. It repaired more of the
audited tactical mistakes and scored **1 win, 0 draws, 1 loss against v1.51**.
That tied pair does not demonstrate an overall playing-strength advantage.
v1.51 remains available as a fallback. No Elo estimate is established for v1.52.

## What changed

The engine now includes bounded check extensions, a verified shortcut for finding
a legal pawn move, a correction for overvalued passed pawns facing a queen, and
bounded evaluation of coordinated attacks near a king while a queen remains.
The last term reuses existing attack counts rather than scanning the board again.
The v1.51 startup fixes, trained player policy, optional Alien Gambit, endgame
tables and120+0.5 clock controller remain unchanged. This release changes engine
search/evaluation; it does not contain newly fitted neural weights.

Eight new correctness cases passed, covering independent attack-set calculations,
color symmetry, scope, bounded scoring, terminal priority and interrupted-search
state restoration. All40 timed/node-limited position probes passed legality,
state and runtime checks. Repeated original mistakes fell from14/17 to8/17 in
the one-second clock probes. Mean regret fell from340.53/374.82cp to240.24/253.41cp
at the two teacher budgets, with no new stable200cp regressions or mate losses.
The motivating king, endgame and rook criteria passed. The king fix applied to
the clock probe; the separate250k-node probe still chose the old Kf1 move.
These are exposed diagnostic positions, not independent rating evidence.

## Completed games

Exactly two serial games at120 seconds plus0.5 seconds per move, from one
preselected B89 Sicilian Sozin/Sherbakov opening, with both colors:

| Opponent | Wins | Draws | Losses | Runtime or clock failures |
|---|---:|---:|---:|---:|
| Chessity v1.51 | 1 | 0 | 1 | 0 on either side |

v1.52 lost as White and won as Black; both games ended in checkmate. The White
loss lasted116 plies after the prepared start, the Black win46. Candidate
initialization took64.901s and47.467s respectively. All moves, clocks, sources,
opening assignments and outcomes were audited. No extra games were added after
the result. Both Black sides winning the same opening emphasizes the limited
coverage; the runner's single-pair bootstrap interval provides no useful rating
confidence. v1.51 is the only opponent this build has beaten so far, and it has
no calibrated Elo. Earlier wins against nominal2600 belong to older builds.

Strict read-only validation passed:74.974s initialization, two legal calls at
120000ms, maximum move3.487s, peak working set235,466,752 bytes. Filesystem
mutations, network and subprocess operations were blocked. Optional Alien
preparation and elementary endgame checks passed. These are local Windows
checks, not a guarantee about every launch or the organizer's environment.

## What its mistakes identify next

The offline teacher reviewed all81 own moves, screening at20k nodes and verifying
suspicious choices at80k/320k. It found two finite errors of at least200cp at
both budgets, both in the operational middlegame category:

| Game | Played | Verified alternative | Regret at80k /320k |
|---|---|---|---|
| White loss, move24 | c4 | Nf6+ | 630 /653cp |
| Black win, move15 | ...Qxf8 | ...Nxf8 | 431 /484cp |

The White loss's first verified warning was a squandered advantage in the
middlegame; it eventually ended in the endgame. The finite screen did not locate
a stable competitive-to-losing transition, so the exact cause remains unresolved.
Ten mate-scored positions remain separate from finite errors. The Black win
also contained a missed advantage and is retained as an improvement target.

Next engine work should examine these concrete checking and recapture sequences,
including why the search misses the stronger continuation. Useful learning comes
second: any fitting needs verified descendant/opponent-line targets compatible
with the current correction scale. These games supply targeted data; no broad
GM download or long consistency study is needed. A small rated screen of the
same frozen build can report actual opponent results without changing its weights.

## Download and provenance

ZIP SHA256: `72604b1b50c2e22200b70068d8ab98d25a96b586a20278ae465c464cd77ee2c8`.
ZIP size:273,199 bytes. All53 numbered versions throughv1.52 are preserved in
development order. Public downloads require no repository write-access grant.
No live competition submission was made.

[Tactical rule and full results](TACTICAL_PILOT_29_20260908.md) ·
[Practical rule](KING_COORDINATION_PRACTICAL_20260908.md) ·
[Selection record](evidence/king-coordination-practical-20260908/selection.json) ·
[Complete two-game results](evidence/king-coordination-practical-20260908/cycle-29-pair/comparison-compiled-king-coordination-v1/results.json) ·
[Phase diagnosis](evidence/king-coordination-practical-20260908/cycle-29-review/phase.json) ·
[Evidence manifest](evidence/king-coordination-practical-20260908/manifest.json) ·
[Previous v1.51 results](STARTUP_RECOVERY_RESULTS_20260908.md)


## Completed rated screen:8September

The subsequent four-game120+0.5 screen finished **0W1D1L against nominal2400**
and **0W0D2L against nominal2600**. All losses were checkmates; the draw was
threefold repetition. No candidate or opponent runtime/clock failures occurred.
This build has beaten neither rated setting. Its only beaten opponent remains
v1.51, with no calibrated rating. No overall superiority or reliable Elo is
established; the recommendation remains provisional.

The173-move teacher audit found first warnings and losing transitions in the
middlegame for all three losses, although each ended in the endgame. Five finite
200cp errors were retained. Next work traces the actual played and alternative
lines before changing search/evaluation or fitting again.

[Full rated results and mistake analysis](KING_COORDINATION_RATED_RESULTS_20260908.md).
