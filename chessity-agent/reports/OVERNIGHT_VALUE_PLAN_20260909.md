# Stage3: rule-aware value learning with independently labelled descendants

Stage1's geometry and hash/scout trials failed. Stage2's shallow-check budget
completed an extra ply at the critical late loss but chose the sameRa3 move;
16-root mean regrets118.97/135.38cp became120.69/135.78cp, no100cp repair. No new
major/mate failures appeared, but the quality gate failed. Retain53 unchanged.

We now test learning that changes the values of future positions, separately
from root preference fitting. The previous37-row Hamming-centre model is not
reused. It overfit local positions and failed both position and game checks.

First independently label up to192 quiet descendants from the eight reviewed
games. Choose negative and positive source decisions before measuring endpoints;
take best/played teacher-continuation prefixes2/4, retaining full actual history.
Each endpoint receives its OWN80k/320k analysis. Reject checks, terminal/twofold
positions, near-draw clocks, mate scores, magnitudes>1500cp or disagreement>100cp.
Parent move rewards are provenance, never copied into static value labels.

Assign whole starting-position/game groups to training/validation before labels,
keeping all four E55 local games together; deterministic grouping aims at two of
eight games for validation. Remove exact/mirror collisions. Historical theory
exposure remains a limitation; this is diagnostic generalisation, not fresh Elo.

Proposed architecture for the next implementation: original781-input/64-unit
clipped-ReLU residual, adding four perspective-relative castling flags, eight
legal en-passant-file flags and a bounded halfmove-clock feature to768piece-square
features. Keep piece accumulators incremental. Pack rule weights alongside output
weights so recursive search signatures need not grow. Retain classical evaluation,
terminal rules, a bounded correction, and a guarded use near repetition/draw clocks.

Train one fixed bounded fit with broad existing CC0 engine-labelled data and the
new training descendants; keep held-out descendant groups out of optimisation.
The300k dataset hasfen/cp/split/group; old annotations have uncontrolled teacher
versions/depths and contain mate encodings, so filter finite|cp|<=1500 and use its
existing ECO split. Recompute the53 baseline values rather than reuse an older
classical evaluator's cached values. Protect held-out exact/mirror positions.

Before implementation/training, fix the concrete optimiser, epoch and blend
selection rules in a separate preparation record. Validate gradients and agreement
between full versus incremental/rule-aware inference. Static error improvements
only permit a small move-quality and runtime check, then shortfeedback_matches.
No architecture, weights, release or improvement is claimed merely by this plan.

## Concrete next-fit bounds fixed before looking at validation outcomes

- One original random781x64 clipped-ReLU hidden layer, bias0.25, initial output0,
  seed202609092330. No published/pretrained network and no local Hamming centres.
- Up to20,000 broad training and2,000 broad validation positions, using existing
  ECO partitions; verify the legacy cp side-to-move convention from its builder.
  Use independent eligible descendants in their frozen game-group partitions.
  Remove exact/mirror cross-partition collisions before fitting.
- Twenty fixed epochs, batch256 broad plus up to64 game-balanced target positions,
  gradient mixture0.75 broad/0.25 target, Adam learning rate0.001, weight decay1e-5,
  Huber loss with200cp scale. Targets are teacher-minus-exact53 classical scores,
  clipped to±600cp for the bounded residual. No epoch/seed/hyperparameter sweep.
- Runtime residual bounded±600cp. Choose blend from0,0.25,0.5,1 ONLY using broad
  validation after fitting, then evaluate the untouched descendant holdout once.
  Require at least2% lower broad validation MAE and10% lower descendant validation
  MAE before spending a runtime/move probe. These thresholds don't establish Elo.
- Piece weights768x64 and bias64 maintain two perspective accumulators. Store
  output64 plus rule_weights13x64 in the model; the driver can pack these into a
 14x64 array passed through the existing output argument. At evaluation, row0 is
  the readout; rows1–4 encode ownK/ownQ/opponentK/opponentQ castling, rows5–12 legal
  EP files, row13 halfmove_clock/70. This avoids another recursive search argument.
- Preserve original static evaluator and terminal rules. Disable neural correction
  at halfmove_clock>=70 and at repeated leaf positions that it cannot represent.
  Check finite-difference gradients, full versus incremental/rule inference across
  special moves, and strict read-only operation. Do not claim a speed gain from the
  larger network without measurement. No failed search prototypes bundled by default.
