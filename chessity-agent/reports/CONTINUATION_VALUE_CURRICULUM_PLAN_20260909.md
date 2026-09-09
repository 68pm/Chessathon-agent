# Bounded sixteen-unit position-value trial

Start from exact selected v1.56, preserving all releases and rejected trials.
The recent public games have unknown executable versions. Their positions are
development evidence, not a new rating test. The new 3% allocation optimisation
failed its predeclared 5% gate and is excluded from this value trial.

Use 17 relevant master games already collected, with three complete fresh TWIC
games reserved before labels. The two Closed Sicilian games were previously
available and are training only. Keep raw TWIC downloads and PGNs local, as the
source notice specifies personal use. No runtime teacher lookup or PGN payload.

Prepare actual legal positions with full histories at plies20/28/36/44/60/80 in
training games and20/26/32/38/44/50/56/62/68/74/80/86 in reserved games. Check all
reserved full-game positions against fit rows using FEN/mirror keys. No reserved
labels until weights freeze. Exact/mirror duplicates and conflicting labels are
excluded; whole-game reservations are distinct. Older broad development data and
earlier exposed holdouts are never described as fresh independent validation.

Label suitable GM positions independently at80000 and320000 teacher nodes. Reject
mate, terminal, check, repetition, draw-clock>=70, abs(cp)>1500, and disagreement
>100cp. Retain excluded records. At most120 planned positions and48M teacher nodes
across train and reserved stages. Recent student leaves require the same filters
and a complete quiescence/static gap<=75cp. Root rewards are not leaf labels.

Fit a new randomly initialised768x16 clipped-ReLU residual network, eight fixed
positive and eight negative readout units. Input weights and biases learn; signed
outputs remain fixed at62.5cp per unit. This extends the existing runtime-supported
width from the rejected eight-unit fits, and includes quiet endgames because the
runtime has no phase gate. Original broad CC0 labels retain their ECO split.
Use up to12000 broad train and1200 development rows including up to3000/300
endgames (phase<=8). Exact/mirror collisions are removed across splits and against
all reserved GM positions. Broad annotation versions/depths are uncontrolled.

Seed2026090917,24 epochs, hidden-only Adam0.001, broad/target gradient mix80/20.
Balance positive/negative corrections in each minibatch. Select epoch/blend
(0.25 or0.5) using reused broad development data only after requiring: broad
capped MSE at least1% better; positive/negative cohort MAE and each represented
phase MAE no worse; recent descendant MAE at least5% better; GM training MAE no
worse. No hyperparameter changes after viewing results in this consumed trial.

Then freeze weights before requesting reserved labels. At least12 eligible new
reserved positions, no exact/mirror overlap with any fit row, MAE no worse and
count of >=200cp errors no greater than baseline are required. Reserved games
share opening families with training: this checks unseen positions within those
families, not broad out-of-distribution generalisation. On failure retain v1.56.

A passing fit is not a strength claim: first verify runtime numerical feature and
incremental accumulator parity, read-only startup and legal timed moves, then
short tactical/defensive comparison against v1.56. Only a qualifying runtime
candidate proceeds to about6–8 reviewed120+0.5 games against exactv1.56/v1.53 and
nominal2400/2600. A clean2600 win is required before conditional2800. A practical
advantage is required for packaging and authorised automatic competition upload.
All work serial, normal capacity/STOP checks, deadline17:45BST; no old jobs resumed.
