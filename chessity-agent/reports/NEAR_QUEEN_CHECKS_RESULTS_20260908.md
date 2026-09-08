# Near-queen checking continuation: tactical gate passed

The prototype now recognizes both diagnosed mate-in-six continuations and
avoids the original Bxf2+ blunder in the clock probe. The frozen cycle35 gate
passed. **This is a development result; a separate read-only check and two-game
comparison are required before selecting a new upload.** No new neural fit or
calibrated Elo is claimed.

The search activates a bounded continuation when the attacking queen approaches
the opposing king. Up to four quiet checks can follow the ordinary checking
captures, while the checked defender retains all legal evasions. Existing
quiescence depth12 and overall ply96 limits remain. TT context distinguishes
quiet-check capacity and attacker; evaluation, policy, weights, root selection,
clocks and startup code are unchanged. Cycle31 root PVS is not included.

| Verified mating position | Zero quiet credits | Four quiet credits | Nodes with four credits |
|---|---:|---:|---:|
| After Kh1 dxc5 | -404cp | Mate score29989 | 4,751 |
| After Kh1 Qxc5 | -373cp | Mate score29989 | 1,080 |

Both full-window quiescence searches found mate in six within their500k-node/
8-second limits, taking0.024s and0.006s. Geometry matched python-chess over240
deterministic positions for both colors. With quiet credits disabled, all five
prior depth6 forced-branch scores AND node counts matched unchanged v1.52.
Checkmate priority at100 halfmoves, stalemate, a512-node interrupt, and
piece/state/accumulator/real-history restoration checks passed.

| 21 one-second development probes | Selected v1.52 | Prototype |
|---|---:|---:|
| Repeats of original played mistakes | 12 | 11 |
| Teacher mean regret,80k | 258.71cp | 236.86cp |
| Teacher mean regret,320k | 276.67cp | 255.76cp |
| Initialization | 67.227s | 73.106s |
| Largest clock-probe wall time | 1.015s | 1.008s |

All42 probes completed legally within their bounds. The motivating Black root
changed from Bxf2+ to Qd3, within50cp of the verified best at both budgets. Mean
regret decreased at both budgets with no new stable paired200cp errors or mate
losses. Teacher review reused existing evidence and requested480,000 new nodes.
These exposed positions do not independently measure whole-game strength.

The first priority, engine search, now addresses the diagnosed forcing sequence.
Learning should retain its mate outcomes and opponent continuations rather than
fit a misleading favorable leaf. The separate exchange-ending value error
remains unresolved. The existing21 roots and two mating positions supplied the
targeted data; no new game collection or neural update was needed.

The tactical task finished on8September at14:48:23BST and was removed after
verifying its successful exit and no owned processes. The exact tested bytes
were frozen for the separately predeclared practical follow-through. See
[original rules](IMPROVEMENT_CYCLE_35.md), [practical rules](NEAR_QUEEN_CHECKS_PRACTICAL_20260908.md)
and [all evidence](evidence/near-queen-checks-20260908/manifest.json).
