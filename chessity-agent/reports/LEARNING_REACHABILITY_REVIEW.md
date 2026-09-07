# Why some replay targets exceed the network's allowed correction

A small read-only review of the completed mistake-replay pilot found a mismatch
between several training targets and the correction the runtime can express.
This review used existing JSON records and saved weights, with no search,
Stockfish calls, new training or changed model selection. Heavy work remains
blocked by disk capacity.

The experimental runtime clips the network's raw correction to 500 centipawns,
then applies its fixed 0.25 blend. Its actual correction is therefore limited
to **125 centipawns in either direction**. Across the pilot's nine branch pairs:

| Diagnostic | Result |
|---|---:|
| Endpoint teacher targets outside that correction range | 14 of 18 |
| Requested pair margins impossible even at the extreme corrections | 2 of 9 |
| Final targeted-model endpoints beyond the hard output clip | 4 of 18 |
| Final matched-control endpoints beyond that clip | 0 of 18 |

One impossible margin belongs to training and one to the held-out family. For
the held-out round54 position at ply50, the classical endpoint gap is -158cp.
Opposite 125cp corrections can increase it to at most +92cp, below the requested
200cp margin. For the training position `newest-vs48:game-002-ply-056`, the maximum
is +155cp, also below its requested 200cp margin. The script checks these bounds
by enumerating all four extreme correction combinations, including perspectives.

This does **not** mean the correct root move is impossible: a positive branch
gap smaller than the training margin can still rank the better endpoint first,
and actual search may reach different leaves. Nor does this prove the sole cause
of the failed held-out or ordinary-game results. It establishes that fitting all
the requested numeric targets exactly was impossible under this runtime cap.

The four clipped targeted endpoints also have zero derivative through the hard
output clip in the existing learning code. That is a local gradient limitation,
not a claim that the entire model stopped learning: other endpoints, broad replay
and parameter regularization can still change shared weights. The saved-model
calculations use vectorized inference; they are not a new compiled-runtime parity
check or fresh generalization test.

## Implications for the three priorities

**Engine first:** complete the pending startup/protocol repair when capacity
returns. The quiet Rc1 defence also remains a search-depth issue; these static
endpoint observations cannot replace useful calculation.

**Learning second:** before another fit, explicitly compare each objective with
the allowed runtime correction. A subsequent bounded experiment could test a
range-compatible objective with the same 125cp runtime cap and equal-compute
control. Its gradients, held-out choices and real-clock performance would need
verification. Do not simply increase the blend or replay unchanged epochs: the
earlier full-weight model already failed practical selection. No such experiment
has been run or promoted by this review.

**Data third:** the nine existing pairs and saved candidate/control weights were
enough to identify the mismatch. More broadly collected GM games would not change
these algebraic limits. Keep endpoint values, root-choice quality and final game
outcomes as separate measurements when deciding whether a future change helps.

Evidence: `learning-reachability-01/report.json`, with every endpoint, model and
dataset hashes, per-branch correction bounds and saturation observations.
Source: `scripts/replay_capacity_review.py`. Protected input hashes were unchanged;
fitted updates and new teacher nodes were both zero. v1.41 remains selected.
