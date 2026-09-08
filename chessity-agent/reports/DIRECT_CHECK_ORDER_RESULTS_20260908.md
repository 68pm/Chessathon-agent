# Direct checking-move ordering result

**Selected upload remains v1.51.** The ordering prototype failed its original
tactical gate. Ten correctness cases passed in83.00seconds, including independent
direct-check geometry and completed depth3 score parity with the parent on six
roots. Only check ordering differs from the two-extension parent; all other
submitted runtime files and weights remain those of51.

Original clock mistakes repeated on17 roots: selected51
13, prototype
13. King choice changed away from Kf1:
True. Initialization took
44.218s and 53.929s.
All40 probes were legal, restored state and met their time bounds. Fixed-node
diagnostics are separate from clock decisions; raw records identify whether
the full node limit was reached.

The cheap gate failed, so no new teacher analysis was run.

| Build | Audited position | Mode | Move | Completed depth | Nodes |
|---|---|---|---|---:|---:|
| baseline | startup19-game-001-ply-062 | clock | g1f1 | 7 | 167936 |
| baseline | startup19-game-002-ply-021 | clock | f5f4 | 5 | 118784 |
| baseline | startup19-game-003-ply-068 | clock | d8d3 | 5 | 139264 |
| baseline | startup19-game-001-ply-062 | nodes | g1f1 | 7 | 250000 |
| baseline | startup19-game-002-ply-021 | nodes | f5f4 | 6 | 250000 |
| baseline | startup19-game-003-ply-068 | nodes | d8c8 | 6 | 250000 |
| prototype | startup19-game-001-ply-062 | clock | g1g2 | 6 | 279552 |
| prototype | startup19-game-002-ply-021 | clock | f5f4 | 6 | 211968 |
| prototype | startup19-game-003-ply-068 | clock | d8c8 | 5 | 129024 |
| prototype | startup19-game-001-ply-062 | nodes | g1g2 | 6 | 250000 |
| prototype | startup19-game-002-ply-021 | nodes | f5f4 | 6 | 250000 |
| prototype | startup19-game-003-ply-068 | nodes | c3d5 | 6 | 250000 |

The failed gate does not qualify this prototype for packaging or the proposed two-game pair. Keep51 and preserve every outcome; do not rerun the unchanged pilot.

No new fitting, broad data collection or ordinary games occurred in this pilot.
Engine work tested useful forcing-move search efficiency; learning remains a
separate need for compatible opponent-continuation targets. Existing audited
histories and verified alternatives supplied the data, including14 compatible
teacher-cache records preserved in an immutable seed file. No Elo inference
or stronger-agent claim follows from these deliberately exposed root tests.

[Predeclaration](IMPROVEMENT_CYCLE_25.md) ·
[Gate result](evidence/direct-check-order-20260908/cycle-25/gate.json) ·
[Complete evidence](evidence/direct-check-order-20260908/manifest.json) ·
[Selected agent and actual matches](IMPROVEMENT_RESULTS.md)
