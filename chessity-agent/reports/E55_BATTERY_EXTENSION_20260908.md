# One-ply bishop–queen threat extension

Exact53 E55 losses/draw were reviewed:236 own moves,49.7M requested teacher
nodes. A supplementary four-position80k/320k/1.28M review found the missed
transition20...Qxc6 versus...bxc6: best-143/-120/-80, played-515/-542/-518.
21.Rxe4 and the bishop–queen attack explain the danger after...fxe4 Bxe4.
The supplemental script's reason string calls its last root14...Na4; the saved
FEN/actual move and all labels correctly refer to14...Qh4. Keep this correction
explicit rather than altering frozen evidence.

One new search hypothesis from unchanged53: at a quiet horizon (qdepth<=4),
if a queen's diagonal through one friendly bishop reaches the enemy king ring,
search one full legal ply instead of stand pat. The trigger applies to either
colour and preserves quiet defensive alternatives. A single extra credit per
line bounds it, and the credit is included in transposition context. Other
blockers stop the ray; the helper grants no score or mate. Existing near-queen
checks, two checking extensions, clock/node bounds and terminal rules remain.

Test the trigger with an independent python-chess ray oracle over all4games and
mirrors, blockers, and state restoration. Then17 equal1s roots per build: all9
paired200cp errors from the4games, all4 supplemental roots, and4 prior repaired
or drawn public-game controls. Policy disabled equally, fresh tables each root,
90s init and1.25s bound. Serial hidden Normal4, >=2048MiB disk/768MiB RAM before
each child. No games or teacher overlap. Freeze every source/target before run.

Independently review new root choices at80k/320k, reusing identical cached
choices. Maximum13.6M new requested nodes. Acceptance requires at least one
100cp repair at both budgets, fewer paired200cp errors, lower mean regret at
both budgets over common finite cases, no new paired200cp or mate-loss mistake,
and legal/restored/on-time probes. Do not change thresholds after results.
These exposed cases measure a proposed correction, not generalisation or Elo.

A passing candidate receives a read-only check and a short same-opening colour
pair against53, then the authorized2400/2600 rematch. Qualify a new upload only
with clean operation and >=50% in the53 pair.2800 requires a played2600 win.
No long study. Rejected candidates and every loss remain recorded. This trial
changes search code, not neural weights; the draw/conversion problem remains a
separate targeted need if its decisions do not improve.
