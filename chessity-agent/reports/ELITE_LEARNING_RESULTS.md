# Elite-case outcome-guided learning pilot

**Recommended upload: chessity-agent v1.14.**

## Data and actual learning

The supplied Markdown provided 22 case entries: 21 distinct legal positions from 20 games. The referenced 1,862-game companion corpus was not present and was not used. Independent 80k/320k-node teacher verification accepted 20 cases and quarantined 1. Supplied cases lack full preceding game history, a limitation kept in their metadata.

The existing 935–64–32–1 move-ranking network received the verified cases alongside train-only Carlsen/Witty, puzzle and three-phase replay. The classical evaluator, search, original clock controller and optional Alien preference were copied from the preserved best. Prose explanations were converted to board/move supervision; this network does not ingest or reason over the document's text.

After every adaptation game, every recorded ply was submitted for independent Stockfish review. Stable candidate decisions, corrections and refutations entered the next weight update; unstable or non-exact mate-scored roots were quarantined. Opponent moves were reviewed as context and never treated as the candidate's rewarded choices. Lost games still supplied corrected targets.

The outcome branch mixed up to 10% extra probability into a verified sound move from a win (5% for a draw). It reinforced 77 distinct sampled sound choices, including 0 from wins. This is outcome-guided supervised learning, not a policy-gradient reinforcement-learning algorithm. A terminal result never becomes a forced-win label for an earlier position. A matched teacher-only branch trained on the same examples and update schedule without the outcome bonus.

Epoch zero remained eligible: a training update was retained only when it improved the fixed validation objective (50% broad, 30% phase, 20% puzzle cross-entropy). Whole known source games and exact/mirrored validation-board collisions were excluded from replay. Unknown older source identities and related positions remain possible. Training games changed checkpoints after each game and are excluded from strength estimates.

| Training stage | Branch | Selected epoch | Parameter L2 change |
|---|---|---:|---:|
| seed | teacher_only | 4 | 0.760112 |
| seed | outcome | 4 | 0.760112 |
| after-game-01 | teacher_only | 2 | 0.459602 |
| after-game-01 | outcome | 2 | 0.459602 |
| after-game-02 | teacher_only | 0 | 0.000000 |
| after-game-02 | outcome | 0 | 0.000000 |
| after-game-03 | teacher_only | 2 | 0.471992 |
| after-game-03 | outcome | 2 | 0.471943 |
| after-game-04 | teacher_only | 0 | 0.000000 |
| after-game-04 | outcome | 0 | 0.000000 |
| after-game-05 | teacher_only | 1 | 0.312334 |
| after-game-05 | outcome | 1 | 0.312310 |
| after-game-06 | teacher_only | 1 | 0.306416 |
| after-game-06 | outcome | 1 | 0.306270 |
| after-game-07 | teacher_only | 1 | 0.301959 |
| after-game-07 | outcome | 1 | 0.301987 |
| after-game-08 | teacher_only | 2 | 0.434134 |
| after-game-08 | outcome | 2 | 0.434179 |

## Fresh frozen evaluation at 120+0.5

| Opponent | W | D | L | Score | Paired 95% score interval |
|---|---:|---:|---:|---:|---|
| candidates/classical-witty-magnus-v1 | 5 | 2 | 9 | 37.5% | [0.15625, 0.59375] |
| candidates/elite-teacher-control-v1 | 3 | 1 | 4 | 43.8% | [0.125, 0.6875] |
| stockfish:2400 | 1 | 1 | 14 | 9.4% | [0.0, 0.21875] |
| stockfish:2600 | 0 | 5 | 11 | 15.6% | [0.03125, 0.28125] |

Highest nominal setting defeated by the new candidate in fresh games: 2400. Promotion: Fresh paired 95% lower score bound versus the preserved best did not exceed 50%. The outcome candidate scored below 50% versus the matched teacher-only ablation.

The practical consistency target requires the lower 95% Wilson bound on outright wins to exceed 50% at each setting. Wilson intervals assume independent game outcomes; the accompanying paired bootstrap reflects opening-pair clustering. This small fixed pilot cannot certify future win rates, hardware independence or a human/site rating.

- stockfish:2400: outright-win interval [0.01111934476464252, 0.28328737570298945]; pilot criterion not met.
- stockfish:2600: outright-win interval [0, 0.1936076805344365]; pilot criterion not met.

## Training-case recognition

| Build | Raw-policy accepted | Verified blunders |
|---|---:|---:|
| candidates/classical-witty-magnus-v1 | 16/20 | 2 |
| candidates/elite-outcome-g08-v1 | 18/20 | 1 |
| candidates/elite-teacher-control-v1 | 18/20 | 1 |

These are training-case recall measurements, not new held-out tactical strength or actual search choices.

## Per-game review coverage

| Training game | Score | All plies attempted | Verified plies | Verified own moves | Verified own blunders |
|---|---:|---:|---:|---:|---:|
| 1 | 0.0 | 118 | 96 | 47 | 2 |
| 2 | 0.5 | 159 | 145 | 75 | 0 |
| 3 | 0.5 | 87 | 81 | 42 | 0 |
| 4 | 0.0 | 49 | 42 | 19 | 0 |
| 5 | 0.0 | 100 | 68 | 31 | 0 |
| 6 | 0.0 | 63 | 31 | 15 | 1 |
| 7 | 0.0 | 64 | 48 | 22 | 1 |
| 8 | 0.0 | 75 | 31 | 10 | 0 |

All 64 game records passed schedule, legal-move, clock, increment and frozen-runtime audits. The selected ZIP passed read-only execution checks. Offline Stockfish executables and teacher labels are excluded from competition archives. The two-round budget ended as declared; no extra games were added to chase a high-rated win.
