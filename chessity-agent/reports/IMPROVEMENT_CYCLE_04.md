# Cycle 04 — convert a measured class of missed endgame wins

The incumbent is v1.41. The table-only successor compiled-rook-bishop-v1 adds
complete rook-and-bishop versus rook WDL/DTZ data and capture closure. See
IMPROVEMENT_ENDGAME_TARGET.md for source verification, the draw-rule correction,
the original-history conversion replay, and package checks. Search, trained weights,
opening preferences and clock allocation are identical to v1.41. The separate
late-move reduction experiment is not mixed into this candidate.
The frozen candidate is archived publicly as experimental v1.43.

Predeclared hypothesis: exact data for a demonstrated missing material class will
improve conversion without changing ordinary middlegame calculation. Correctness
gate passed: nine endgame tests,18 new KRBvKR conversion drills including the
mirrored target, original-history replay, and strict read-only package validation.
No new network fit or additional player-history download is warranted for this gap.

After cycle03 finishes, run eight paired development games against v1.41 and four
each against nominal2400/2600 at120+0.5 on the exposed elite opening set, offset0.
At most two concurrent games; do not overlap controllers' match workloads. Audit
all games, then screen every rated own move and verify suspicious decisions at
the existing fixed teacher budgets. Endgame cases used here are development data.
Do not treat an exposed conversion drill as a rated victory or promote on it alone.

This fixed16-game schedule is a regression/development screen and may contain few
five-piece endings. It cannot establish a rating or consistent2600 wins. Do not
extend it to chase a win. Review scope-specific conversion evidence and ordinary
outcomes before deciding a fresh confirmation or a further engineering cycle.
v1.41 remains the upload recommendation while this runs.

Next potential search hypothesis, not implemented: a board-matching transposition
entry can order an already generated legal move even when its repetition context
differs. Reusing its score/bounds must continue to require the current history and
halfmove checks. That separation may save search work without weakening draw
correctness. Require explicit poisoned-context tests and equal-depth score checks
before measuring throughput or spending another match budget.
