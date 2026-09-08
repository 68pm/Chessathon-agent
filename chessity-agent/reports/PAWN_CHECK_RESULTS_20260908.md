# Pawn-proof and check-extension combination

**Selected upload remains v1.51.** The new combination failed its predeclared
tactical gate. The earlier pawn-proof pair and rejected check-extension/ordering
results remain preserved; none was reclassified or repeated to obtain this result.

Six new interaction checks passed in76.58seconds, with exact completed depth3
scores AND node/interrupt counters matching parent23 on six roots. Nine unchanged
donor tests were retained through their XML hash and exact function/dependency
parity. All40 new position probes were legal, restored state and met their bounds.
Initialization was 46.402s for selected51 and
54.281s for the prototype.

Original mistakes repeated on17 clock roots: selected51
14, prototype14.
King changed away from Kf1 in at least one mode:True.
Clock decisions and node diagnostics remain distinct.

The cheap gate failed; zero new teacher nodes were requested.

| Build | Position | Mode | Move | Completed depth | Nodes |
|---|---|---|---|---:|---:|
| baseline | King | clock | g1f1 | 7 | 168960 |
| baseline | Rook | clock | d8d3 | 5 | 183296 |
| baseline | King | nodes | g1f1 | 7 | 250000 |
| baseline | Rook | nodes | d8c8 | 6 | 250000 |
| prototype | King | clock | g1g2 | 6 | 209920 |
| prototype | Rook | clock | d8c8 | 5 | 220160 |
| prototype | King | nodes | g1g2 | 6 | 250000 |
| prototype | Rook | nodes | c3d5 | 6 | 250000 |

The failed gate does not qualify for packaging or the proposed pair. Keep51 and diagnose the remaining weakness without an unchanged retry.

The code change reuses the proven sufficient pawn-move legality test to reduce
quiet-leaf terminal-check cost while retaining two check-extension credits.
Weights, evaluation, ordering and clocks remain unchanged. Learning is still a
separate need for runtime-compatible targets that include verified opponent
continuations. Existing audited games and teacher references supplied the data.
No fitting, broad downloads or ordinary games ran in this pilot.

[Predeclaration](IMPROVEMENT_CYCLE_26.md) ·
[Gate](evidence/pawn-check-combination-20260908/cycle-26/gate.json) ·
[Complete evidence](evidence/pawn-check-combination-20260908/manifest.json) ·
[Selected agent](IMPROVEMENT_RESULTS.md)
