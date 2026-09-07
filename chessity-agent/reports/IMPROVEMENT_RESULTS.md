# Current selected agent: chessity-agent v1.41

**Recommended competition upload: v1.41.** The exact ZIP is available through the latest download. It passed the predeclared independent promotion rule over v1.14. The continuing 2600 programme remains active.

| Opponent | Wins | Draws | Losses |
|---|---:|---:|---:|
| v1.14 | 23 | 1 | 0 |
| stockfish:2400 | 3 | 4 | 1 |
| stockfish:2600 | 0 | 3 | 5 |

All 40 games used 120+0.5 and passed legal-move, clock, increment, outcome and frozen-source audits, without runtime failures. The comparison used 12 distinct paired starting groups; the rated tests used 4 further groups in both colours. The conservative comparison score lower bound was 58.7%, above 50%, with attempt-adjusted alpha 0.025. It assumes independent groups and stable conditions.

Highest nominal setting defeated in this set: **2400**. These Stockfish handicap numbers are not calibrated Chess.com/FIDE ratings. This sample does not establish consistent 2600 wins or the strongest possible engine. Earlier development and failed experiments remain visible; no games were added to chase a win.

The improvement comes from our original compiled search, faster quiescence terminal checks and exact elementary endgame tables. It preserves the previously trained Classical/Witty/Magnus root policy and bounded optional Alien preference. The new residual network did not demonstrate a matched playing-strength gain and was not merged into the selected runtime.

Strict read-only/no-network/no-subprocess inference passed, including table probes. Initialization was 28.80s and peak measured memory 229.6MB. Only original Python source and own weights plus attributed permitted table data ship; compilation occurs in memory. The prior full suite passed 108 tests, and four additional successor-data tests passed separately.

ZIP SHA-256: `e4b66bd0f5a16418a49119c0547a818c3bb79a3c9e209b3eca7210907e072f63`. All 48 chronological versions through v1.47 remain available. No competition upload or repository write-access grant was performed.

Later experimental v1.42 achieved a verified checkmate win against nominal2600:
its complete four-game result was1W/2D/1L. It scored2W/0D/2L at nominal2400 and
1W/5D/2L against v1.41, so it was not promoted. This is a development milestone,
not a rating or consistency claim. The winning PGN and all losses are published
with the [cycle03 critique](IMPROVEMENT_CYCLE_03.md).

The v1.43 table experiment fixed a measured conversion in drills but no ordinary
game reached its added coverage; its comparison also failed to establish a gain.
The v1.44 move-order experiment finished2W/2D/4L versus v1.41,3W/1D/0L at nominal2400
and0W/0D/4L at nominal2600; it was not promoted. All 16 games were audited.

The matched supervised pilot trained score-only v1.45 and preference-learning
v1.46 from the same weights and data. Held-out pair ordering improved from2/6 to3/6,
but the complete24-game screen did not establish stronger play: v1.46 scored
2W/3D/3L against v1.45,1W/2D/5L against v1.41,1W/1D/2L at nominal2400 and
0W/2D/2L at nominal2600. All24 games passed independent audits. See
[cycle06](IMPROVEMENT_CYCLE_06.md). The full-weight model is not promoted.

Experimental v1.47 applies the same learned correction at one quarter of its old
weight. On six selected failure positions it reduced independently checked mean
move regret at both80k/320k teacher budgets; only800k new teacher nodes were needed
by reusing identical analyses. It still missed the bishop-trapping threat and
repeated four original errors. Read-only inference passed. Its fixed16-game screen
finished2W/5D/1L against v1.41,2W/1D/1L against nominal2400 and0W/1D/3L against
nominal2600. All16 completed games passed independent audits; no promotion. An external process interruption
left one completed draw; that result and unfinished snapshots were preserved,
and the unchanged remaining schedule resumed. See [cycle07](IMPROVEMENT_CYCLE_07.md).
No promotion follows from the selected diagnostic, and consistent2600 is unmet.

Exposed positions/groups remain development data and cannot become fresh
confirmation. The full-project backup is a separate earlier snapshot; current
source and evidence are preserved in Git.

The [phase diagnosis](IMPROVEMENT_PHASE_DIAGNOSIS.md) reuses40 completed games and
2,169 audited own moves. Four of v1.41's five2600 losses ended in the endgame, but
the first verified losing transition was middlegame in two, endgame in one and
unresolved in two. Threat calculation and conversion both remain priorities.
Future iterations review code, descendant-position learning and targeted data in
that order. Keep a fixed-strength focus; retire2400 only after independent winning
consistency and replace it with2800, and similarly2600 with3000. Neither level has
qualified. The selected download remains the byte-identical v1.41 archive.
