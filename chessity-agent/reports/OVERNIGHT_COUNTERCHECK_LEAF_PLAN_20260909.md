# Shared-budget defensive counterchecks and root-level value scope

Guarded-leaf-02 failed its declared gate. Preserve its four repairs and two new
major-error counts. The fresh bounded D65 trace found Qb6 after Qxd4, but valued
that position near equality. At greater depth it preferred Rg1+, still missing
the stronger Qd6 queen exchange. This does not prove any single search defect
caused the game result; the following is a new, falsifiable coverage hypothesis.

Correction to earlier prose: the drawn game's move35 alternative is **Qd6**,
not Bd6. All saved UCI targets and preparation SAN were already correct. The
rook-losing candidate capture is **Qxd4**. Preserve the hashed earlier document
and this correction rather than silently altering frozen evidence.

The existing quiescence extension locks its quiet checks to the side that first
activated a near-king queen attack. Test allowing the defender's legal quiet
counterchecks within that same four-credit budget after activation. Both sides
share and decrement the original budget. Check evasions, captures/promotions,
stand-pat, maximum quiescence depth, mate/draw rules and search stops remain.
No nonchecking quiet move or independent second check budget is added. The
existing conservative geometry prefilter avoids unnecessary make/unmake work.

Fix the learned evaluator's opening scope at the root: searches starting through
move12 use blend0 throughout, even if a long continuation crosses that boundary.
This also skips unnecessary accumulator updates during those searches. Later
roots retain the declared half blend, capped300cp, and classical ending gate.
Use a distinct multiplier for the neural transposition context; the prior draft
reused the quiet-budget multiplier, permitting swapped-context XOR aliases.
Root blend0 uses tag0, separating its values from enabled later-root searches.

Reuse the fixed rule-value checkpoint byte-for-byte, with no new fit or training
data. The exact pawn-mask efficiency implementation remains. Treat all26 roots
as exposed development cases, including the D65 paired game; no rating or
independent strength claim follows from their replay. This is a combined
integration candidate, not an isolated attribution study of the two changes.

Before timing, require feature/oracle and restoration tests plus new coverage
tests: a defender's legal quiet check is visited only after activation and while
credits remain; quiet nonchecks remain excluded; state and budgets restore;
opening root scope is passed correctly; TT values distinguish activation and
budget contexts, including the previously aliased state pair. Freeze sources
and ZIP first. Preserve every failed attempt.

Then use the same26-root,104-probe ABBA one-second comparison against the
compiler-repaired53 control, startup below90seconds, serial teacher80k/320k
review. Require at least one100cp repair, nonincreasing mean regret at both
budgets and no increased major/mate-error counts per root. A pass permits the
existing read-only validation and four-game120+0.5 comparison, then conditional
2400/2600/2800/3000 pairs. Keep v1.53 selected until practical evidence warrants
change. No long consistency study or unchanged failed retry.
