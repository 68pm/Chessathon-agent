# Targeted descendants after the pawn candidate's short screen

The first 2400 game identified king-safety errors. At move23, Qc2 was preferable
to Bf4. At move24, the defensive sacrifice Nxf7 was preferable to Nh3, which led
to Bxh3 and gxh3, opening the king's shelter. Both budgets rated the Nh3 choice
about300cp worse. Later moves occurred in an already losing position; they must
not be presented as the original cause of the loss. Root rewards remain policy
signals; independently labelled descendants are needed for value training.

After the complete frozen screen and its per-game reviews, select each game's
first two negative roots satisfying the value-domain filter, plus one supported
positive root near the middle of the eligible positives. Follow four plies of
the already reviewed deeper best and played lines for negatives, and the played
line for positives. Keep all histories. Exclude duplicate/mirrored, terminal,
checked, repeated and low-phase positions using the existing domain filter.

There are at most five planned descendants per game and50overall, including any
conditional2800pair. Each gets its own80k/320k teacher analysis. Accept only finite
nonmate values within1500cp that agree within100cp. Never copy a root score or
reward, and never turn a mate estimate into a fabricated centipawn target. The
maximum new node request is20million; cached answers reduce actual work.

These are exposed development/training positions. Their C09/D28/D65 opening
groups are excluded from validation in the prepared signed-value learner. Training
does not change a frozen playing comparison or prove a rating. The signed-value
source was explicitly revised before either preparation or fit ran to require this
completed label batch alongside the earlier archive dataset. Its source and dataset
provenance will be frozen at preparation. Heavy labelling waits until the controller closes
and capacity is available, with the daytime deadline and STOP guards.
