# Precompute fixed evaluation terms without changing scores

Both contact-mate trials corrected direct terminal detection but failed to repair
the tested root choices. Preserve those failures and return to the first priority:
make searched positions cheaper before adding more search work or training data.

The exact selected v1.55 evaluator recalculates the material and piece-square
formula for every occupied square at every evaluated leaf. Precompute those fixed
integer terms for both colours at module startup. Replace only that formula with
table lookups. Pawn structure, mobility, king pressure, tapering, conversion,
policy, learned weights, search and rule handling remain byte-for-byte or AST
equivalent. No unselected fast-legal, mate detector or value fit is bundled.

Check 1,200 deterministic legal positions and their colour mirrors against the
preserved v1.55 evaluator with conversion both off and on, all twelve existing
diagnostic roots, promotions, en passant and castling. Verify exact integer scores
and state restoration, then AST isolation of every other function.

Use the preserved twelve-root ABBA harness: fixed 250k-node searches with a 12s
cap and one-second production searches. Require exact fixed-work move, score,
depth and node parity; >=5% aggregate and median CPU improvement; no reduction in
mean completed one-second depth. Only a pass proceeds to independent 80k/320k
teacher review, with no added major/mate error and nonincreasing finite regret.

Only both gates passing permit a short 120+0.5 match screen. Retain v1.55 until
practical evidence justifies a successor. These roots are exposed development
positions, not Elo calibration. All work remains serial and bounded by existing
capacity, STOP, owned-process and daytime deadline checks.
