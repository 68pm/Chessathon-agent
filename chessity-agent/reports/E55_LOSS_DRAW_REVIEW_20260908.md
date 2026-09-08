# Review of the two fresh losses and draw

Review all four exact v1.53 E55 games: 2400 White checkmate win and Black
checkmate loss; 2600 White threefold draw and Black checkmate loss. Export each
original PGN and verify its final board. Include the win as a control, retain
all mistakes and actual histories. These are known v1.53 games, unlike the
uncertain version attribution in the older public dashboard games.

Screen every candidate move at 20k best/played nodes, verify suspected errors
at 80k and 320k. Maximum requested nodes are 840k times the frozen own-move
count; account before each call. No games, JIT or fitting during this review.
Single teacher thread, 32MiB hash, hidden Normal priority4 launch after direct
2048MiB disk and 768MiB RAM checks, maximum capacity wait20min. Check STOP
before each teacher call. Never retry unchanged attempts or discard outcomes.

Reuse labels for phase analysis and distinguish the first stable deterioration
from the terminal position. Inspect the draw for lost advantages as well as
successful defensive repetition. Nominal opponent settings are not a measured
Elo. The same opening and small colour sample limit generalisation.

Next use the findings to select one concrete engine/search or independently
labeled descendant-value correction, with a bounded regression gate before a
short new match screen. No broad data imports, blind epochs or long consistency
study. A successful candidate should face 2400/2600 again, then 2800 only after
a played 2600 win. Keep v1.53 as the current upload until a successor qualifies.
