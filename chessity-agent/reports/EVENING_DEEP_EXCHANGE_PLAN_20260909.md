# Exchange-aware ordering below the root

The fitted tapered head failed both exposed colour gates despite a broad MSE
gain, so its weights stay out and the three reserved Italian games stay unseen.
No new network fit follows. The next engine iteration targets the order of
opponent continuations: the earlier bounded exchange trial only inspected root
and immediate replies. Test the same original legal-recapture estimator at ALL
main-search nodes of depth>=3, on exactv1.56 with buffered move ordering.

For a more valuable piece capturing a cheaper one, inspect at most six legal
recaptures on that square. Demote a negative estimate below quiet moves, retaining
the move for full search. Preserve checking moves/evasions, promotions, en-passant,
uncertain long exchanges and transposition hints. No move deletion, extra pruning,
new reduction rule, changed evaluator, clocks or failed experimental components.
The existing tested estimator is unchanged; the new coverage and buffered caller
are the experiment. Avoid quiescence-node estimation cost.

Verify legal-recapture oracles, restoration, retained moves and exact parity
between buffered/unbuffered scores. Then use the unchanged12root evening ABBA
clock/teacher gate, with adaptive deep labels for23Re6. No new major/mate errors,
no higher mean regret at either budget,>=10% improvement at one budget. Only a
pass permits the same reserved strict>=3/4 versusv1.56 and rated/read-only gates.
For targeted data, retain every changed root's independent analysis. Do not
assign those action rewards as descendant values or fit during a playing screen.
