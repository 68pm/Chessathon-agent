# Balanced signed value experiment

The completed student-descendants-01 diagnosis has 62 independently labelled
positions and 42 eligible finite, stable labels. Matched static MAE was 291.27 cp
and quiescence MAE 267.23 cp. Some errors remain near 500 cp after capture search;
one 858.5 cp static error shrinks to 7.5 cp after capture search. These are exposed
diagnostic positions, not a strength measurement or unseen validation.

Prepare one new experiment, balanced-value-01. Retain the signed eight-unit
clipped-ReLU architecture and fixed four +125/four -125 cp readouts. Change the
training objective through balanced sampling: each broad batch has 112 negative,
112 positive and 32 near-zero teacher-minus-classical corrections; each targeted
batch has 16 negative and 16 positive corrections. Keep the 80/20 gradient mix,
learning rate .001, 16 epochs and existing .25/.5 candidate blends. This is a new
objective and new targeted data, not a rerun of the failed signed-value fit.

Reuse the existing broad training/development-validation rows and original target
labels. Add independently labelled student/teacher descendants only when active,
stable and the completed quiescence score differs from static by at most 75 cp.
This filter prioritises valuation errors that immediate capture search does not
already remove. Preserve all excluded labels for diagnosis. Remove exact/mirror
duplicates and conflicting targets; never average conflicting histories blindly.
Recalculate base values with the exact selected v1.55 classical evaluator.

Known C09/D28/D65 target ECO groups remain excluded from broad validation. The
new public round76 game lacks an ECO header; group its descendants by that game
identity and disclose that semantic opening overlap with the broad corpus is
uncontrolled. Its game and exact/mirror positions are excluded from evaluation.
Broad validation is reused development data. Save every epoch checkpoint and
both correction-cohort errors for every blend, including rejected epochs.

Require at least 1% better broad capped MSE, at least 5% better target MAE, and
no increase in either broad positive/negative correction-cohort MAE. The new
descendant cohort must also improve at least 5%. Select only among qualifying
epoch/blend pairs using broad validation MSE; otherwise stop before teacher work.

If a fit qualifies, freeze its weights before evaluating descendants of the
24 split2 roots reserved by signed-value-01. That failed trial never labelled or
evaluated those descendants, so they remain unused reservations. Preserve their
group exclusions and exclude all earlier exposed root/leaf exact/mirror keys.
Follow four independently analysed teacher plies, then label eligible endpoints
at 80k/320k nodes. Maximum requested teacher work is 11.52 million nodes. Keep
mate/uncertainty exclusions, require at least 12 eligible endpoints, nonworsening
mean absolute error and no increase in errors of at least 200 cp. After this use,
these positions are exposed and cannot be reused as fresh validation.

This training trial creates no playing release. Runtime integration must handle
the eight-unit shape, domain gates, accumulator parity, search cost and read-only
startup before tactical checks and a short comparison against the selected v1.55.
Keep the selected ZIP unchanged unless those later practical gates justify a new
version. Use serial CPU work, capacity/STOP checks and the daytime cutoff.
