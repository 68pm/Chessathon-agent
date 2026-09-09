# Combine legal-existence speed with selected move-buffer reuse

Currentv1.56 reuses move/ordering storage but its terminal-existence helper still
builds an entire pseudo-legal move list. The earlier king-step helper saved15%
on itsv1.55 parent but its two-game direct comparison drew twice and failed.
Preserve that result; do not select or rerun that old candidate. The new parent
hasv1.56's separate buffers at each search ply. Test their interaction by adding
ONLY the unchanged king-step-first helper to exactv1.56. This is a new combined
engine; neither component's older timing or match wins transfer automatically.

One legal king step proves move existence; if none is found, use the original
complete fallback. No evaluation, move ordering, pruning, histories, draw rules,
clocks or trained weights change. Validate helpers against python-chess and check
buffer storage after interleaving existence queries. On the12evening roots run
250k-node fixed-work and1second ABBA probes. Require all tests, exact fixed-work
move/score/depth/node parity, >=5% aggregate AND median CPU gain, no lower mean
clock depth. Do not repeat timing or relax thresholds after a failure.

On a speed pass, independently review all clock choices with unchanged adaptive
teacher budgets:80k/320k except23Re6 at2.56M/10.24M. Require no new major/mate
errors and non-increasing mean regret at both budgets. For this exact speed
experiment, the speed gate supplies the measured improvement. Practical proof
still requires the same reserved>=3/4 versusv1.56, rated2400/2600 and read-only
gates. Existing unsuccessful value/evaluation/search changes are excluded.

Targeted data are the recent actual mistakes and current independent labels.
The new tapered fit failed both colour checks; its weights and three untouched
Italian reservations remain separate. Every ensuing game must be reviewed.
