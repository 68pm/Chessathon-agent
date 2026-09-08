# Queen-aware evaluation with bounded check search

**Selected upload remains v1.51.** This prototype failed its predeclared
tactical gate. The report preserves every result; it does not create a numbered
release or infer a playing rating.

New correctness cases passed: 6 in 64.54s.
Retained prior evidence: retained_queen_cases=6. See the combined correctness record
and predeclaration for the distinction between newly executed and reused checks.
All 40 position probes were legal, restored state and met their time bounds.
Initialization: 57.299s baseline,
69.236s prototype.

Original mistakes repeated on 17 clock roots: baseline
14, prototype 12.
King choice changed away from Kf1 in at least one mode: True.

Mean clock regret at 80k/320k: 340.53/374.82cp for the baseline, 265.00/293.12cp for the prototype.

New stable paired 200cp regressions: 1. New mate losses: 0.

King choice within 50cp at both budgets: True.

New teacher nodes requested: 0.

Endgame clock choice within 50cp at both budgets: True.

Regressions: startup19-game-003-ply-068.

| Build | Target | Mode | Move | Completed depth | Nodes |
|---|---|---|---|---:|---:|
| baseline | Promotion | clock | f7e8 | 7 | 207872 |
| baseline | King | clock | g1f1 | 7 | 160768 |
| baseline | Rook | clock | d8d3 | 5 | 111616 |
| baseline | King | nodes | g1f1 | 7 | 250000 |
| baseline | Rook | nodes | d8c8 | 6 | 250000 |
| prototype | Promotion | clock | b4b7 | 6 | 135168 |
| prototype | King | clock | g1g2 | 6 | 152576 |
| prototype | Rook | clock | d8c8 | 5 | 128000 |
| prototype | King | nodes | g1g2 | 6 | 250000 |
| prototype | Rook | nodes | c3d5 | 6 | 250000 |

This failed gate does not qualify for packaging or the proposed pair. Keep the selected agent and diagnose the remaining issue without an unchanged retry.

These are exposed diagnostic positions, not held-out game-strength evidence.
No model fitting, broad downloads or ordinary games ran as part of this pilot.
The predeclaration explains the engine change, implications for useful learning,
and targeted data rationale. Compatible existing teacher evidence is reused;
no threshold was changed after observing outcomes.

[Predeclaration](IMPROVEMENT_CYCLE_27.md) ·
[Gate](evidence/queen-check-combination-20260908/cycle-27/gate.json) ·
[All evidence](evidence/queen-check-combination-20260908/manifest.json) ·
[Selected agent and actual matches](IMPROVEMENT_RESULTS.md)
