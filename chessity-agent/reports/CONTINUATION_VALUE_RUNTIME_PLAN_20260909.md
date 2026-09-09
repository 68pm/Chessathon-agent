# Runtime gate for the frozen curriculum value fit

The completed first fit passed its declared development and29-position reserved
checks. These GM checkpoints all occurred on even plies (White to move). The
broad and recent student training data include both colours, but the GM colour
coverage is limited. Before runtime work, independently test Black-to-move plies
21/33/45/57/69/81 from the same three reserved game groups with the already frozen
weights. Exclude exact/mirror fit collisions. At least9 eligible examples, MAE
no worse and no more >=200cp errors required. No refit or blend adjustment.

The core's feature and accumulator loops support16 units, but the selected
driver's file loader asserts32 units. In an isolated copy of exactv1.56, change
only that shape assertion to16, add the trained16-unit file, and enable it at
the already selected0.5 blend. All other sources, policy, optional opening
preference, clocks, search and tables remain byte-identical. Default32 zero arrays
for model-free use remain valid; no algorithm port or external network.

Before timed comparisons, verify both-perspective feature sums and evaluation
against an independent dense calculation. Test incremental make/unmake against
full reconstruction over seeded legal play plus castling, en-passant and all
promotions; require board/state restoration, <=1e-9 accumulator differences and
<=1cp integer rounding difference. Startup<90s; no additional JIT signatures
after warmup on searched paths; candidate files remain frozen.

Compare six recent exposed critical roots plus six older development roots at
one and three seconds, ABBA order, two repeats per engine. Histories restored,
search tables cleared before each probe, one active engine at a time. Independently
review every distinct chosen move at80000/320000 nodes with the same board history.
No new >=200cp mistakes or forced mate losses at either time budget; at least
six finite comparable roots; strictly lower mean regret at both teacher budgets
at three seconds, and no worse means at one second. This is a targeted development
gate, not a rating estimate. Failing candidates receive no long match screen.

If these gates pass, strict read-only package validation and the authorised short
120+0.5 version/2400/2600 screen follow. Qualifying2600 played win required for2800.
No release or automatic upload until practical comparison demonstrates advantage.
