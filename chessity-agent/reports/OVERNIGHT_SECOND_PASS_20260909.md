# Overnight second checkpoint: compiler repair measured, v1.53 retained

No successor has qualified for release at this checkpoint. All54numbered archives
and the selectedv1.53ZIP remain unchanged. No new full local games have been played;
the candidate gates stopped those experiments before matches.

| Experiment | Completed evidence | Decision |
|---|---|---|
| Quiescence cache | Exact depth-two parity;1.0856aggregate CPU ratio | Below1.10speed gate |
| Classical-only kernel | Original53control startup exceeded90s before prototype measured | Incomplete pair; separate prototype-only read-only check passed at76.278s |
| Bitset attacks |18compiled checks;176probes; exact250knode parity;1.1933CPU ratio | Mean1sdepth4.4545->4.3636failed combined gate |
| Bounded queen-check defence |15checks including1,174positions/mirrors | Prototype startup exceeded90s; no position result |
| Explicit root argument types |11checks; prototype80.574s/two search variants | Original53control exceeded90s; no probes |
| Complete recursive argument typing |12checks; one search variant;62.373s versus81.199s startup | Passed startup/efficiency gate; failed subsequent timed-choice quality |
| Defence plus complete compiler repair |10integration checks, reusing15compiled defence checks; prototype64.412s/one variant | Original53control exceeded90s; no position probes |

The complete compiler repair reduced startup by23.19%. All176probes completed;
fixed-work scores, moves, depths and node counts matched53exactly. Aggregate CPU
ratio was.9908, with mean1sdepth4.2273versus4.1818. This is an initialization
improvement with essentially unchanged search throughput, not an Elo improvement.

The subsequent independent80k/320k review of22clock roots requested1.2Mnew teacher
nodes. Mean regret changed126.068->128.727cp at the smaller budget and
149.568->146.091cp at the larger one. Paired-major-error counts increased at
round72move9and field Istanbul move34; no100cp repair or new mate loss was found.
The declared quality gate failed, so no package validation/game/release followed
for that candidate. Timing varied; fixed-work equivalence does not certify every
choice selected under a short wall-clock limit.

The next separate trial uses the same compiler repair in both control and defence
candidate, isolating the defensive feature and avoiding the repeatedly failing
original-control startup. That control hasv1.53search logic/weights but is not the
exactv1.53ZIP. This pending comparison is excluded from the completed evidence here.

## Learning diagnosis

Saved predictions from the rejected value fit improved12of17middlegame positions,
but worsened5of6openings and all8endgames. Endgame MAE rose174.94->235.90cp;
only one of all31targets exceeded the600cp correction range. The fit's aggregate
5%gain concealed uneven transfer. No weights were mixed into the retained upload.
These already exposed holdout details are development evidence for a later recipe,
not fresh validation. [Stage diagnosis](OVERNIGHT_VALUE_DIAGNOSIS_20260909.md).

## Retained benchmarks and upload

Exactv1.53latest E55 screen at120s+0.5s:2400 **1W/0D/1L**;
2600 **0W/1D/1L**. Across all8exactv1.53rated games:2400 **1W/1D/2L**;
2600 **0W/1D/3L**. Highest clean nominal opponent beaten:2400once.
No exactv1.53win against2600or result against2800/3000is recorded here.
These handicap settings do not establish a calibrated rating.

The latest imported public competition sample remains1W/1D/1L for an unverified
uploaded build; do not add those results to exactv1.53local statistics.
Selected ZIP SHA256:
5747acec37da25ea79704e49d19e45bf23bd2af5842a14eaf66bf6ecf2791315.

The07:20BST report remains scheduled. Later completed evidence or a qualifying
release will be reported separately; this checkpoint does not claim completion
of the overnight improvement request.
