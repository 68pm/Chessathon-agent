# Perspective-difference value experiment

The completed balanced-value-01 fit passed its development gates but worsened
mean error on 22 unused descendants from 283.18 to 286.50 cp. It added more than
1 cp to 18 of those positions and subtracted more than 1 cp from four. Keep that
failed trial and all its exposed evaluation positions intact.

The next experiment changes the residual architecture to
`0.5 * (network(our piece perspective) - network(their piece perspective))`.
The two inputs describe the same pieces; swapping channels and reflecting ranks
changes the feature perspective. It creates no new teacher label or purported
legal game position. A common optimistic output cancels. This models positional
advantage only: real chess also depends on tempo, so the constraint may lose
useful information and must demonstrate an advantage in tests.

Keep the same 13297 rows, 97 targeted labels, balanced batches, signed eight-unit
head, 80/20 gradient mix, learning rate .001, 16 epochs, .25/.5 blend options and
development gates as balanced-value-01. Save every checkpoint and cohort metric.
The 32 new descendant targets remain development data. Fresh initialisation uses
seed2026090912. This is an architecture experiment, not a repeat of the failed fit.

Before training, reserve 24 new split2 roots from the original CC0 dataset, at
most two per ECO group. Exclude all groups reserved by the earlier daytime small,
signed and balanced value trials, known target groups, and every protected earlier
root/leaf exact or mirrored position. Do not use the failed balanced holdout for
new model selection, fitting or fresh evaluation. Public round76 has no ECO label;
preserve its game grouping and disclose uncontrolled semantic opening overlap.

Development gates remain: at least 1% lower broad capped MSE, nonworsening MAE in
both positive and negative broad correction cohorts, at least 5% lower target
MAE and at least 5% lower new-descendant MAE. Stop before further teacher work if
no epoch/blend qualifies. Otherwise freeze weights, then derive four teacher plies
from each new reserved root and independently label endpoints at80k/320k nodes.
Allow at most11.52M requested teacher nodes. Require at least12 stable eligible
endpoints, nonworsening mean absolute error and no increase in >=200cp errors.

Perspective conversion, antisymmetric predictions and independent finite-difference
gradients passed three tests before fitting. Passing a value test is not a release:
runtime integration, eight-unit shape/domain handling, accumulator parity, speed,
tactical quality, read-only startup and short games against v1.55 remain required.
Use serial CPU work, capacity/STOP checks and the daytime deadline. Keep the
selected v1.55 ZIP unchanged during the experiment.
