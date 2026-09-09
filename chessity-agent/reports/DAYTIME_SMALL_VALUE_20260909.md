# Eight-unit searched-position value pilot

After the first two engineering gates, retain exact v1.42 as the baseline.
Its runtime currently disables residual value. Train a new eight-unit clipped
ReLU residual from our own random initialization, using 768 side-to-move piece
inputs. A smaller hidden layer is intended to limit per-move accumulator cost;
actual runtime timing is still required. Keep classical evaluation for phase <=8.

Use 12,000 broad CC0 positions from split 0 and 1,200 from split 1, preserving
ECO group separation. Add eligible independently labelled middlegame descendants
from the completed 58-position archive review to training only. Exclude C09/D28
from broad validation/test and remove exact/mirror collisions. Their earlier
train/validation designation is explicitly superseded: both are exposed here.

Reserve 16 roots from source split 2 before fitting, at most two per ECO group.
These groups are absent from this fit's train/validation. They are unseen by
this new value fit, not a claim that the historical source pool was never used
in any older diagnostic. After freezing the fitted weights, follow up to four
teacher PV plies from each root and independently label each eligible endpoint
at 80k/320k nodes. Never assign a root score to an endpoint. Exact/mirror endpoint
collisions with training/validation invalidate that holdout item. Do not fit again
after seeing holdout results. Preserve mates/uncertainty and reconstructed history.

One deterministic 16-epoch fit: seed 2026090903, 256 broad and 32 targeted samples
per step, 80/20 gradient mixture, Adam LR .001, weight decay .00001. Targets are
teacher-minus-exact-v1.42-classical residual in 200cp units, clipped to +/-2.5.
Select epoch/blend from broad validation only (blends .25 and .5, raw cap500cp).
Assess the original teacher values, not clipped training targets, in all metrics.
Require >=1% broad capped-MSE gain, >=5% target MAE gain, >=8 eligible unseen
endpoints, no worse holdout MAE and no more >=200cp holdout errors.

This static gate cannot promote a playing agent. A passing model still needs
exact training/runtime feature and accumulator tests, a bounded eight-unit
runtime integration, strict read-only/startup checks, timed tactical comparisons
and the short reviewed playing screen. Failed fits remain saved and unselected.
Do not ship teacher-labelled position lookups or external chess networks.
