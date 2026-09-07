# Independent improvement confirmation 01

Declared before its games: use frozen compiled-qsearch-endgames-v1, combining the
original compiled classical search, early-exit terminal legality check, existing
v1.14 root policy/optional Alien hint, and exact elementary tables. The residual
network tied its matched control2W4D2L and is not selected by its lower static MSE.
No learned weight averaging is performed.

Budget:12 distinct held-out-ECO starting groups, both colours, against v1.14 (24games).
Then4 further groups, both colours, at each nominal2400/2600 setting (16games).
120+0.5, at most2 simultaneous games. No training or teacher analysis during matches.
Use confirmation-starts/starts.json offsets0 and12 respectively. This is the first
independent confirmation attempt in this new programme; all results will be retained.
Start selection used source-test-split positions and a fixed balance verifier, never
candidate outcomes. Earlier root policies can know related opening theory.

Promotion requires all scheduled games and source/clock/legality audits to pass,
strict read-only package checks, and a one-sided score lower bound above50% against
v1.14. Treat each colour pair as one bounded observation and use the conservative
Hoeffding lower bound: mean minus sqrt(log(1/alpha)/(2*number_of_pairs)).
Allocate alpha=0.05/(attempt*(attempt+1)), hence0.025 for attempt1. This summable
schedule accounts for repeated confirmation attempts; it assumes independent opening
groups and stable conditions, and cannot cover opponent calibration or host drift.
Unlike the small bootstrap screen, this bound does not collapse when all results agree.
No runtime failures by either side may support promotion.

This may establish a provisional improvement over our incumbent. It cannot establish
a human/site Elo or the programme's consistent2600 target. The latter still requires
the larger independent qualification blocks defined in IMPROVEMENT_LOOP.md.

After these frozen matches, save the review and audit rated-game errors. Those game
positions then become development material for later candidates and must not be reused
as fresh confirmation. Continue with a new measured hypothesis; do not add games to
this schedule to chase a preferred result.
