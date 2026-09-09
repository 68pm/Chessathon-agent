# Signed position-value learner — prepared 9 September 2026

The failed small-value-01 fit produced eight positive output weights (51.89 to
59.93cp). With nonnegative clipped-ReLU activations, that frozen model can only
increase its classical value. It predicted a positive correction for92.17% of
the1200 validation positions, although only63.08% needed one. Broad mean error
improved, but new descendant MAE worsened218.43 ->232.14cp. This is a concrete
training limitation; it does not prove the sole cause of failure. Teacher-best
moves were quiet in12/14 held-out positions, including several harmful corrections,
so unsettled captures alone do not explain the failed fit.

Prepare one new eight-unit clipped-ReLU residual with four fixed+125cp readouts
and four fixed-125cp readouts. Train input weights and biases with the same Huber
gradient,16epochs,256broad+32target batch and80/20 gradient mixture. No published
network is used. The signed fixed readout prevents all output signs collapsing
positive; it does not guarantee good predictions. The existing runtime format
can represent these weights, but no runtime candidate is created by training.

Reuse the12000/1200 broad split and eligible archive descendants, adding the
independently labelled current-screen descendants from signed-targets-01. This
unconsumed-source revision follows the new 2400 king-safety loss; no fit or target
preparation had run before the change. Keep exact and mirror duplicates out;
exclude every conflicting duplicate when its independently labelled values differ
by over100cp. Before fitting, reserve24 new split2 source roots, at most2perECO,
excluding all groups exposed in small-value-01's reserved holdout and every
target-training ECO group (including C09/D28/D65). Exclude its actual root and
descendant positions too. Existing broad
validation is development data for model selection, not a fresh external test.

Choose epoch/blend by broad validation with an extra constraint: mean absolute
error must not worsen in either correction cohort (teacher-classical<=-25cp or
>=25cp), each with at least50positions. Keep runtime correction capped500cp
before blend. If broad capped MSE fails to improve1% or target MAE fails5%, stop
before spending any new teacher nodes.

For a fit passing those development checks, freeze its weights, then follow four
teacher PV plies from each reserved source and independently label each eligible
endpoint at80k/320k nodes. No root reward is copied. Preserve mate/uncertain labels
and existing phase/repetition exclusions. Require at least12stable eligible leaves,
nonworsening mean error and nonincreasing >=200cp errors. Do not reuse this exposed
holdout as fresh evidence after a failed attempt. This retains the earlier leaf
protocol to test the signed-head change; actual quiescent-leaf training remains
a separate possible experiment. This trial changes the signed readout and adds
targeted screen data, so any improvement must not be attributed solely to one.

Run only after the current bounded match controller exits and its owned workers
close, in the value-learning stage of the ordered plan. Honour daytime capacity,
STOP and15:40cutoff guards. Runtime integration, accumulator/feature parity,
strict read-only startup and short playing comparisons remain mandatory for any
later selected release. The current playing candidate and v1.42 remain untouched.
