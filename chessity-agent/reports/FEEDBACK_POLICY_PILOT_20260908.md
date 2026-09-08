# Small reward-policy check, declared before fitting completes

Compare the unchanged v1.53 policy against the new reward-policy checkpoint on
12 exposed competition roots, with the policy enabled and a fresh candidate
process for each build. Keep the engine, value weights and runtime options
unchanged. One second per root, cleared search tables, full actual history,
legal move/state restoration checks, initialization below 90 seconds and a
130-second external process cap. Use the existing capacity and STOP guards.

The fixed roots are round 70 moves 14, 15 and 25; round 71 moves 18, 30 and 34;
round 72 moves 9, 18 and 24; and round 68 moves 25, 51 and 80. These cover good
attacks, missed corrections, the new loss and the existing draw. They are
development examples, including training exposure, not a held-out rating test.

Reuse the saved 80k/320k best/played labels and the teacher cache. Independently
score newly selected moves at both budgets. A useful gate requires at least one
100 cp repair at both budgets, lower mean regret at both budgets, and no new
paired 200 cp mistake or newly mate-losing choice. Retain every failure and
unchanged result. No automatic release follows this small gate; a passing
candidate still needs a small practical comparison before promotion.

After the pilot, refine round 72 move 24 at 1.28M nodes for best and played moves,
paired with its existing 320k labels. This is at most 2.56M additional requested
nodes. Preserve the original uncertain review and keep any refined target for
the next training batch; do not claim it was part of the already completed fit.
