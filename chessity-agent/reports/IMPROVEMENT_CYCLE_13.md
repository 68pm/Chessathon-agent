# Cycle 13: prove one legal pawn move before generating all moves

Base: frozen v1.41 alone. At every quiet quiescence node, its stalemate guard
generates the entire pseudo-legal list before testing the first legal move.
For a side already known not to be in check, a one-square pawn push is legal
when its destination is empty and the source shares neither rank, file nor
diagonal with its own king. Removing that pawn cannot uncover a sliding check;
the move does not change a knight or pawn attack on the stationary king.

Use this sufficient geometric proof as an early return in has_legal_move.
Otherwise use the exact existing generator and make/unmake test. No assumptions
about en passant or castling; they stay on the fallback path. No evaluation,
weights, ordering, pruning or earlier failed prototype code is included.

Validate against python-chess legal-move existence on1500 random legal boards,
pins, checks, mate, stalemate, promotion and en passant cases, with state parity.
Use the same11-root250k-node gate and two alternating passes: exact completed
depths, nodes, scores and moves, at least10% aggregate speedup. Stop on failure.
If passed, check package/read-only operation and a two-game colour pair versus41
at120+0.5. These are short development checks, never Elo certification or a long
independent consistency study. Keep41 until practical replacement evidence.

Engine work first. No new learning fit until calculation costs are resolved;
existing diagnosed positions supply the targeted data for this iteration.

Position gate complete: passed. Nine correctness tests passed4.23s. All44
fixed-work results matched exactly across both builds and passes. Baseline
times8.093599/5.378991s; prototype4.239553/4.340747s. Aggregate1.570177x,
but baseline timing varied materially. The smaller corresponding pass gain
was1.239185x; neither number guarantees server performance.

Frozen candidate: compiled-pawn-proof-v1. ZIP SHA256
dc3dddabfb0b0932068e84968232ecbb3d1243e7de709f3b6b56b5a0b3a0dc1a,
272622 bytes,328348 uncompressed. Only engine/compiled_core.py differs from41.

Before match outcomes: use source entry3 from the already prepared consistency
opening file as one colour pair against41, with its recorded legal line. This
is a two-game practical comparison, not resumption of that abandoned study.
Require exact-work gate, read-only runtime checks, all legal/clock/source/outcome
audits, no candidate runtime failures and at least50% score to recommend this
exact search-efficiency revision for the competition. Retain41 as fallback.
The match pair is a sanity check, not a measured Elo gain or proof of stable
superiority. Below50%, keep41 and diagnose the losses without adding a long run.

Read-only check passed: import21.831s, peak234139648 bytes, two legal calls at
120000ms clock, maximum move3.485s. Optional Alien preference and actual elementary
tables exercised; all file mutations blocked, no sockets or subprocesses.
The pair uses A48 Torre Attack/Grunfeld, both colours. Frozen plan SHA256
47a075b528469cd87082ff2d7c4b33470f6b667cdf923e38ff96aa5dcbc17444.

Completed practical pair: **0 wins, 1 draw, 1 loss against v1.41**,120+0.5. All source, legal-move, clock and outcome audits passed; candidate runtime failures=0. Selected download: **v1.41**. This follows the declared practical rule and does not establish an Elo gain or stable superiority. v1.41 is retained.

Post-game feedback is complete, using127 own moves screened at20k nodes and
suspected errors rechecked at80k/320k. Three stable200cp errors were found.
The loss ended in the endgame but first became losing in the middlegame:
23.Ne1 instead of Ne5, with55.36 seconds left, lost at least331cp. In the draw,
28...Bf7 lost at least216cp; the best teacher move differed by analysis budget.
At56...Bxe8, exchanging the bishop allowed the g-pawn to promote and squandered
a winning endgame; ...Rb7 kept a roughly+5-pawn advantage. Verified regret was
488/503cp with18.09 seconds still available. These are finite teacher estimates.

Next investigate those quiet defensive and promotion-guard decisions with short
forced-line traces before choosing a search or leaf-evaluation change. Faster
calculation alone did not pass the practical pair, but one pair also cannot prove
the optimization intrinsically weaker. Preserve both41 and48 for controlled
future combinations. Do not repeat these matches to chase a promotion. No new
weights were fitted: diagnosis must specify a useful learning signal first.
