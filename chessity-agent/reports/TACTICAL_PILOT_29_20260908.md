# Bounded coordinated king-pressure evaluation

**Selected upload remains v1.51.** This prototype passed its predeclared
tactical gate. The report preserves every result; it does not create a numbered
release or infer a playing rating.

New correctness cases passed: 8 in 47.93s.
Retained prior evidence: none. See the combined correctness record
and predeclaration for the distinction between newly executed and reused checks.
All 40 position probes were legal, restored state and met their time bounds.
Initialization: 57.728s baseline,
69.624s prototype.

Original mistakes repeated on 17 clock roots: baseline
14, prototype 8.
King choice changed away from Kf1 in at least one mode: True.

Mean clock regret at 80k/320k: 340.53/374.82cp for the baseline, 240.24/253.41cp for the prototype.

New stable paired 200cp regressions: 0. New mate losses: 0.

King choice within 50cp at both budgets: True.

New teacher nodes requested: 1,600,000.

Endgame clock choice within 50cp at both budgets: True.

Rook choice below 200cp regret at both budgets in both modes: True.

| Build | Target | Mode | Move | Completed depth | Nodes |
|---|---|---|---|---:|---:|
| baseline | Promotion | clock | f7e8 | 7 | 302080 |
| baseline | King | clock | g1f1 | 7 | 180224 |
| baseline | Rook | clock | d8d3 | 5 | 117760 |
| baseline | King | nodes | g1f1 | 7 | 250000 |
| baseline | Rook | nodes | d8c8 | 6 | 250000 |
| prototype | Promotion | clock | b4b7 | 6 | 167936 |
| prototype | King | clock | g1g2 | 5 | 167936 |
| prototype | Rook | clock | d8d3 | 5 | 119808 |
| prototype | King | nodes | g1f1 | 6 | 250000 |
| prototype | Rook | nodes | d8d3 | 5 | 250000 |

A pass permits the declared strict read-only package check and two-game pair. Selection remains pending those checks.

These are exposed diagnostic positions, not held-out game-strength evidence.
No model fitting, broad downloads or ordinary games ran as part of this pilot.
The predeclaration explains the engine change, implications for useful learning,
and targeted data rationale. Compatible existing teacher evidence is reused;
no threshold was changed after observing outcomes.

[Predeclaration](IMPROVEMENT_CYCLE_29.md) ·
[Gate](evidence/king-coordination-20260908/cycle-29/gate.json) ·
[All evidence](evidence/king-coordination-20260908/manifest.json) ·
[Selected agent and actual matches](IMPROVEMENT_RESULTS.md)
