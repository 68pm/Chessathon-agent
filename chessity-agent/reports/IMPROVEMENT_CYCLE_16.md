**Cycle 16: user-requested bounded mistake replay**

The user asked for a few games followed by replaying mistaken decisions until the
bot finds the best move. Use the current ten-game battery, already being played,
and the latest three saved competition games; do not generate another full batch
just to collect data. The user cancelled the Claude request. Analyse locally.
The browser connector currently fails to initialize, so rounds54â€“56 are the latest
saved competition PGNs, not a verified claim that no newer games exist. Their
v1.41 attribution is inferred. Do not analyse older competition builds' histories.

Run only after the ten-game controller and its full post-game audit complete.
Keep v1.41's code, policy, tables and optional Alien preference unchanged. The
first-priority engineering conclusion remains that a targeted evaluator correction
must affect choices deeper in search; preserve the failed search experiments.
The second-priority learning change is a bounded replay loop using the existing
incremental 768â€“32â€“1 residual architecture at a fixed0.25 blend. Reuse our own
learned feature weights but zero the output head, initially preserving classical
values. This is not simply enabling the previous rejected learned evaluator.
The third-priority data source is verified errors from recent games, including
mistakes in wins. No large new archive or Claude transfer.

For each of five source datasets, use at most four accepted/attempted root pairs
through the existing cached successor verifier, with at most two attempts per
game. Both continuations need stable finite80k/320k evaluations. Exclude terminal,
check, repetition-sensitive and near-draw-clock endpoints, exact/mirror duplicates
and collisions with the original broad dataset. Keep all branches from the same
starting family together; the shared A39 starting position across the ten-game
battery is one family, not five independent groups. Hold out a family by counts
and deterministic identity before fitting. If sufficient families are unavailable,
report that limitation instead of silently fitting the test positions.

The selected baseline retries accepted training roots first, at250k nodes and a
20-second safety cap. There are at most three fitting/retry rounds. Each round
uses128 minibatch updates of128 broad training examples, fixed learning rate0.0003,
and the unresolved verified pairs. A matched control receives the same broad
minibatches and update count without the targeted signal. Gradients use the actual
runtime0.25 blend and residual clipping; endpoint loss weight0.25 and paired margin
weight0.1 remain fixed. A root receives at most384 targeted update exposures.

After each round, export a separate model snapshot, retry every training root,
and verify any novel choice at both teacher budgets, using cached results where
possible. A choice within50cp of the reference at both budgets counts as repaired;
several moves may be sound, and finite analysis does not prove an exact unique
best move. Repaired roots leave active replay unless a later round breaks them.
Stop when all training roots meet that criterion or after round3. Stop flags remain
effective. No unchanged-position loop is called learning, and game outcome does
not reward every move in a win.

The final snapshot is chosen by this fixed stop rule. Probe the held-out family
only after fitting, comparing v1.41, the matched control and the replay candidate.
Require more repaired training roots than v1.41, lower held-out mean capped regret
than both comparisons at both budgets, no added verified mate losses, and broad
validation error no more than2% above the better of initial/control. The held-out
family is a small diagnostic, not proof of general playing strength. If the gate
passes, run read-only/package checks and a small real-clock comparison before any
practical promotion. Failed or partial learning is retained and reported honestly.

No external trained network, teacher executable or table of teacher choices enters
the submission. Raw PGNs, theory notes and replay labels remain offline. Keep the
recommended v1.41 ZIP unchanged during this experiment.

**Completed result â€” no promotion**

The pilot finished7 September20:50:36UTC. Four tests passed, including numerical
gradient checks for the actual runtime blend, accepting equivalent good moves
only after both verification budgets, and keeping related starting families
together. Twelve root pairs were attempted; nine were accepted after verification,
with three unstable/out-of-range branches rejected. Seven roots entered replay
and two from the round54 starting family were held out. Existing broad data was
reused; no older competition PGNs or external archive was newly collected.

Baseline v1.41 met the within50cp criterion on1/7 training roots. After actual
weight updates, the three successive snapshots met it on0/7,3/7 and2/7. The final
round remains the candidate under the declared stopping rule; do not select round2
after seeing the result. This confirms learning changed choices, but improvement
was not monotonic and five training positions remained unresolved.

The final replay candidate solved0/2 held-out roots; the matched broad-only
control solved1/2. Mean held-out regret was158/215.5cp for the candidate versus
131.5/187cp for the control at80k/320k nodes. Broad validation capped squared error
improved from91758.14 to80723.54, but the control reached80720.47 without the targeted
signal. A lower static validation loss therefore did not show a useful benefit
from this replay recipe. The declared gate failed. No extra ordinary games,
read-only release probe or promotion were warranted for this failed learning pilot.

All six control/candidate checkpoints, source, teacher attempts, actual choices and
verification records are preserved. v1.41 remains the recommended upload. Do not
repeat this unchanged fit, adjust the threshold after seeing outcomes or claim
that every blunder was cured. The next useful diagnosis is why the corrected
endpoint values failed to improve root decisions, alongside the new candidate's
separate startup failures. Preserve the known Rc1 defensive horizon case and
compare actual search continuations before another fit or architectural expansion.
