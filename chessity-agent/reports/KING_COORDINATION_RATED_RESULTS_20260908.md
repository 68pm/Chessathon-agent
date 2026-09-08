# Chessity v1.52: completed2400/2600 screen

**v1.52 scored no wins in this four-game screen.** It has not demonstrated2400
or2600 playing strength. The candidate remains the provisional upload selected
after its tactical repairs and tied pair against51; these results do not justify
a stronger claim. No additional games were added to chase a win.

| Nominal Stockfish setting | Wins | Draws | Losses | Candidate failures |
|---|---:|---:|---:|---:|
| 2400 | 0 | 1 | 1 | 0 |
| 2600 | 0 | 0 | 2 | 0 |

All games used120 seconds plus0.5 seconds per move, one preselected B73 Dragon
opening with both colors at each level. The2400 draw was threefold repetition;
all three losses were checkmates. Neither side had startup, illegal-move, crash
or flag failures. Candidate initialization took45.551–67.442seconds. Every move,
both clocks, immutable source and outcome passed the existing serial audit.

The strongest opponent v1.52 has beaten remains **Chessity v1.51**, which has no
calibrated Elo. This build has defeated neither rated setting in this screen.
Its separate pair against51 remains1W0D1L. Older builds' wins against nominal2600
are not attributed to52. Four games from one opening cannot establish a defensible
Elo estimate; the degenerate single-pair bootstrap values are not useful intervals.

## Where the games deteriorated

The offline teacher screened all173 own moves at20k nodes and verified suspicious
choices at80k/320k. Five finite errors exceeded200cp at both budgets. All three
losses had their first verified warning and stable losing transition in the
operational middlegame category, then ended in the endgame. This supports working
on middlegame calculation and evaluation first rather than inferring an endgame
cause merely from where checkmate occurred. Finite screens can miss earlier causes.

| Game | First relevant choice | Verified alternative | Finding |
|---|---|---|---|
| Draw as White vs2400, move26 | cxd5 | g5 | Advantage dropped to a drawn assessment;207/293cp regret |
| Loss as Black vs2400, move30 | ...Bxf2+ | ...Qf5 /...Qd3 | Near-equal assessment became losing;505/512cp regret |
| Loss as White vs2600, move26 | gxf6 en passant | Rd3 | Near-equal assessment became losing;481/505cp regret |
| Loss as Black vs2600, move13 | ...Ng4 | ...a6 | Assessment crossed the losing cutoff;156/192cp regret |

The last row is a stable losing transition, not a200cp blunder. The two teacher
budgets disagree on the best queen square in the2400 loss, so retain both
alternatives rather than inventing one certain label. Mate-scored positions and
all later mistakes remain in the raw audit. The draw's squandered advantage is
also retained as a target.

Engine work comes first: compare bounded full-window searches of these exact
played and alternative moves, with actual histories, to see whether deeper
search resolves them or still misvalues the continuations. No engine code or
weights will change during that diagnosis. Useful learning comes second: any
new targets must reflect verified descendant/opponent positions and fit the
runtime correction range. The six recently reviewed games provide targeted data;
no broad GM collection, blind epochs or long consistency study is needed.

The selected v1.52 ZIP remains unchanged:
`72604b1b50c2e22200b70068d8ab98d25a96b586a20278ae465c464cd77ee2c8`.
No new numbered version, trained network, live competition upload or repository
permission change was made for this report.

[Declared four-game schedule](KING_COORDINATION_RATED_20260908.md) ·
[Review budget](KING_COORDINATION_RATED_REVIEW_20260908.md) ·
[All four games](evidence/king-coordination-rated-20260908/king-coordination-rated-01/rated-compiled-king-coordination-v1/results.json) ·
[Phase diagnosis](evidence/king-coordination-rated-20260908/king-coordination-rated-review/phase.json) ·
[Evidence manifest](evidence/king-coordination-rated-20260908/manifest.json) ·
[Original provisional selection](KING_COORDINATION_RESULTS_20260908.md)
