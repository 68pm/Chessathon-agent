# Classical countercheck integration pilot

The calibrated head repaired its33 development positions but worsened both
broad validation and the new22-position grouped holdout. Preserve that failed
fit; it does not enter a playing candidate.

Run one new integration of the exact pawn-mask evaluator, shared four-credit
quiet counterchecks, and process-local NUMBA_OPT=1. The evaluator and runtime
policy are the existing classical ones; no new fitted weights enter this trial.
Compared with the earlier pawn-mask trial, the shared counterchecks and compiler
setting are real changes. Compared with the neural countercheck trial, this
removes neural search plumbing and its startup cost.

Test exact classical evaluation and move restoration against v1.53 and test
that only checking quiet moves spend the existing shared credits. Require cold
prototype startup<=65seconds. Run108 ABBA1second probes on the26 existing roots
plus the recent2400loss's move33. Require nonworsening mean regret at both
Stockfish budgets, no increased major/mate counts, and at least one100cp repair.
All exposed positions are development evidence. Then, only on a pass, run the
existing read-only validation and four-game comparison, followed by small rated
pairs at120s+0.5s with review and conditional ascent. Keep the06:40heavy cutoff.
This trial is not a new selected release or an Elo claim.
