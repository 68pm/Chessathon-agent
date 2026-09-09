# One calibrated value-head experiment

Predeclare a single fit, no hyperparameter search. Keep the 781x64 encoder and
bias frozen. Refit its 64 output weights with weighted ridge regression around
the old output (penalty 50), using residual targets at the actual runtime blend
0.5 and a raw residual cap of1200cp. Runtime correction is therefore capped600cp.
The existing opening and endgame classical gates remain in force.

Use only active middlegame positions (fullmove>12, phase>8). Old broad training
rows have weight1, old targeted training rows weight50, and the independently
labelled D65 descendants weight200. D65 was previously exposed validation: it
becomes explicitly exposed development training in THIS new experiment only.
Original frozen splits and failures remain untouched. Reanalyse the two unstable
Qxd4 descendants at320k/1.28M nodes, accepting only finite, non-mate values within
1500cp and within100cp of each other. Preserve their earlier rejected labels.

Reserve the22 active C09/D28 endpoints from feedback-plan-countercheck-01 as whole
source groups, before new labels. They have no previous independent value labels
or exact/mirrored training collisions. Their games and roots were already seen;
this is a local development holdout, not independent playing-strength evidence.
Freeze the new output weights BEFORE labelling this holdout at80k/320k, using
the same value eligibility rules. Do not fit, select a blend, or tune on it.

Accept static fit only if the new D65 training MAE improves at least10%, the
holdout has at least8 eligible positions and no worse MAE than the old runtime
model, and active broad validation MAE regresses at most2%. All comparisons use
the actual half blend; the old model retains its old300cp effective cap. This
is not an Elo claim. A passed model still needs a new frozen runtime candidate,
startup and short clock-quality checks, read-only validation, and short games.
All new games must use the existing Stockfish review pipeline. No unchanged
retry or deadline extension. Stop checks and serialized capacity rules apply.
