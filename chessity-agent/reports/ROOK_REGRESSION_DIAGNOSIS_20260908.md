# Rook-regression diagnosis

**Selected upload remains v1.51.** All 24 declared forced-branch searches
completed. The regression survives a full-window search with cleared ordering
state, so a root ordering/PVS bug is not needed to explain this observed choice.
The move values change with the search horizon.

Scores below are centipawns from White's perspective, with one root move forced.
The prototype spends up to two check-extension credits, so equal nominal depths
do not represent equal work.

| Build | Depth | Rc8 | Rd3 | Nd1 | Nd5 |
|---|---:|---:|---:|---:|---:|
| baseline | 5 | -148 | -101 | -243 | -187 |
| prototype | 5 | -148 | -253 | -243 | -231 |
| baseline | 6 | -172 | -349 | -248 | -248 |
| prototype | 6 | -270 | -349 | -256 | -253 |
| baseline | 7 | -270 | -349 | -248 | -223 |
| prototype | 7 | -270 | -349 | -248 | -237 |

At depth5, selected51 prefers Rd3 among these moves, while the extension
prototype prefers Rc8. At depth6 the prototype prefers Nd5; selected51 reaches
that preference at depth7. This reproduces the earlier clock/node differences
without root move selection. The deeper branch preference is still inferior to
the teacher's Nd1, and none of these student scores fully reflects the teacher's
roughly -630 to -970cp position evaluations. This identifies a horizon/value
problem; it does not prove that more depth alone will fix the game.

The two initializations took 70.997 and
76.607 seconds. Total student work was
2,174,963 nodes, within the 12 million maximum. All branches restored
board, history and accumulator, remained within500k nodes/8.25seconds, and
completed without interruption. No new teacher calls, fitting, ordinary games,
downloaded data or agent package were needed.

## Next engineering decision

The useful king-defence repair should be retained as a candidate while addressing
its remaining horizon. Inspect a cheap priority for direct checking moves in the
existing quiet-move ordering: the current ordering uses capture/promotion values,
killers and history, with no separate check priority. This is a new hypothesis
for reaching useful forcing branches sooner, not an implemented improvement or
permission to repeat the rejected gate unchanged. Measure search cost and root
choices before deciding whether it belongs in the agent.

Learning still needs opponent counterfactual continuations and targets compatible
with the residual correction limit. Root-position fitting alone cannot teach a
missed future sequence. The exact existing game and verified alternatives are
adequate targeted data for the next bounded step; no broad GM download is justified
by this diagnosis. Preserve the original cycle23 acceptance rule and every loss.

[Predeclaration](IMPROVEMENT_CYCLE_24.md) ·
[All evidence](evidence/rook-regression-20260908/manifest.json) ·
[Previous gate](CHECK_EXTENSION_RESULTS_20260908.md) ·
[Selected agent](IMPROVEMENT_RESULTS.md)
