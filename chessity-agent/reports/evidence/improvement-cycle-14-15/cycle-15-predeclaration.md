# Cycle 15: queen-aware passed-pawn evaluation pilot

Base: frozen v1.48, preserving its exact faster existence guard. The completed
cycle14 trace shows that Bxe8 g8=Q is evaluated about+364cp despite the teacher's
draw assessment. A passed pawn currently receives the same geometric endgame
bonus whether facing a rook or a queen, without modelling checking resources.

Test one bounded correction: at phase<=8, for a side with no queen facing an
enemy queen, reduce only the passed-pawn endgame multiplier from5 to2. Keep
midgame bonus, material values, all other evaluation and search/weights unchanged.
This is a contextual heuristic, not a universal claim that the queen stops every
pawn. The coefficient and scope are fixed before testing; no adjustment retries.

Check exact scope/delta, colour symmetry, random legal-state preservation and
unaffected material classes against the old evaluator. Then use14 exposed errors:
the previous11 roots plus the3 cycle13 errors. At250k nodes, reuse the unchanged
v1.48 cached11-root measurement and measure only its3 new roots, plus all14 for
the prototype. Require fewer repeated errors, avoid Bxe8 at the motivating root,
and verify newly chosen moves with80k/320k teacher nodes. Require lower mean
capped regret at both budgets and no added verified forced-mate losses before
spending time on a small match pair. Preserve all measurements, including failure.

Engine judgement first; review the demonstrated material-context signal for the
residual network second; existing verified mistakes supply targeted data third.
No new fitting, external download, long consistency study or automatic promotion.
