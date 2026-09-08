# Full-window diagnosis of v1.52's four first warnings

The bounded trace completed all27 attempts with5,430,917 student nodes and zero
teacher searches, fitting or games. Initialization took69.676seconds. All18
depth4/6 branches completed; all9 depth8 branches hit the declared500000-node
ceiling and have **null scores**. No depth8 preference is inferred. The largest
branch wall time was4.051seconds; every legality, state and source check passed.

Scores below are from the root mover's perspective, in centipawns. Each branch
started with a cleared transposition table, killers/history and the real game
history. These are full-window forced branches, not repeated live-clock games.

| Game / root choice | Depth4 | Depth6 | Depth8 |
|---|---:|---:|---|
|2400 draw: cxd5 (played)|107|-67|incomplete|
|2400 draw: g5|-28|-28|incomplete|
|2400 loss: ...Bxf2+ (played)|404|378|incomplete|
|2400 loss: ...Qf5|158|57|incomplete|
|2400 loss: ...Qd3|158|57|incomplete|
|2600 White loss: gxf6 e.p. (played)|158|137|incomplete|
|2600 White loss: Rdd3|99|100|incomplete|
|2600 Black loss: ...Ng4 (played)|-35|-50|incomplete|
|2600 Black loss: ...a6|-64|-59|incomplete|

Deeper search changed the draw's preference toward the teacher's g5, although
its value remained much lower than the teacher's estimate. At depth6 the engine
still favored the played move in all three losses. Root policy preferences and
the ordinary root selection procedure are therefore not necessary to reproduce
those wrong rankings. The teacher's80k/320k estimates favor the alternatives,
but this trace alone does not separate missing depth from leaf-value bias.

The fixed depth8 budget was exhausted before a comparison was possible. More
efficient search is worth testing, but no claim that one extra depth fixes the
mistakes is supported yet. Before adjusting evaluation or training, inspect the
actual opponent refutation and the positions the student expects, particularly
the bishop/queen exchange and the en passant rook-fork continuations. A static
root score must not be copied onto every descendant as a training target.

Engine calculation/value accuracy remains first. Useful learning needs verified
counterfactual descendants and an achievable correction scale; no fit is justified
by this trace alone. Targeted data already consist of the four exact positions,
their full histories and the existing teacher continuations. No broad GM data,
unchanged retry, new package or rating claim resulted. Selectedv1.52 is unchanged.

[Predeclared bounds](IMPROVEMENT_CYCLE_30.md) ·
[Full trace](evidence/first-warning-search-trace-20260908/cycle-30/trace.json) ·
[Roots and histories](evidence/first-warning-search-trace-20260908/cycle-30/roots.jsonl) ·
[Evidence manifest](evidence/first-warning-search-trace-20260908/manifest.json) ·
[Actual rated results](KING_COORDINATION_RATED_RESULTS_20260908.md)
