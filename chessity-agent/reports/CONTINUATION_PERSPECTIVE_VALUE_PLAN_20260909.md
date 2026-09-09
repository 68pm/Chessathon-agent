# Isolate the remaining perspective bias

The colour-coverage correction added71 independent Black targets. It still failed
the exposed Black development gate (MAE43.5->60.17), while White improved slightly.
Reject that candidate and preserve it. The three new Italian reserved games have
not received labels and remain unused by training or model selection.

One further bounded architecture test uses the identical13386-row dataset and
the same16-unit initialisation, seed,24epochs and optimisation settings. Change
only the residual to half the difference between the network's two piece
perspectives. The existing tested permutation swaps own/opponent piece channels
and mirrors ranks; it does not create a synthetic evaluation or game history.
The prediction reverses sign if those perspectives swap. This removes a shared
optimism offset; it cannot represent every initiative or zugzwang effect. The
classical evaluator still supplies the base score.

Reuse training/daytime_antisymmetric.py's mathematical forward/gradient helpers,
checking their finite-difference gradients and16-unit perspective identity. The
older eight-unit antisymmetric trial used different data and failed; this is a
distinct16-unit fit with actual-colour GM targets and quiet endgames. No reuse of
that trial's heldout positions as fresh validation.

All earlier broad/cohort/phase/recent/GM gates remain unchanged. The exposed
White and Black development checks must both pass. Only then evaluate the
unlabelled reserved Italian positions with the frozen weights, requiring at
least6 eligible positions of each colour and no worse MAE or >=200cp error count
for either. Do not weaken gates, refit on the reservation or run this fit again.

On success, runtime must use the same half-difference equation, with both
already-maintained accumulators. Numerical make/unmake and full-rebuild tests,
equal-clock tactical checks and the short reviewed match screen remain required.
On failure, finish this bounded task with v1.56 retained and the diagnosis/data
preserved. No extra data dump or long consistency study.
