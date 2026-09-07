# Three-phase pilot results

**Recommended upload: chessity-agent v1.14.**

The candidate keeps the existing locally trained policy and classical evaluation. It changes principal-variation search and quiescence move generation. No neural weights were fitted in this search experiment.

All 92 games passed legal PGN, clock, increment, schedule and frozen-source audits. Time control: 120 seconds plus 0.5 seconds per move; two simultaneous local games, one thread per engine. The local host is shared with other applications.

## Fixed matches

| Build / stage | Opponent | W | D | L | Score | Pair bootstrap 95% |
|---|---|---:|---:|---:|---:|---|
| baseline | stockfish:2200 | 1 | 0 | 3 | 25.0% | [0.0, 0.5] |
| baseline | stockfish:2400 | 1 | 1 | 2 | 37.5% | [0.25, 0.5] |
| baseline | stockfish:2600 | 0 | 0 | 4 | 0.0% | [0.0, 0.0] |
| confirmation | candidates/classical-witty-magnus-v1 | 4 | 7 | 5 | 46.9% | [0.3125, 0.625] |
| confirmation | candidates/fastchess-adaptive-v1 | 3 | 4 | 1 | 62.5% | [0.375, 0.875] |
| rated | stockfish:2200 | 1 | 1 | 10 | 12.5% | [0.0, 0.2916666666666667] |
| rated | stockfish:2400 | 2 | 0 | 10 | 16.7% | [0.0, 0.3333333333333333] |
| rated | stockfish:2600 | 0 | 3 | 9 | 12.5% | [0.041666666666666664, 0.20833333333333334] |
| development-threephase-pvs-v1 | candidates/classical-witty-magnus-v1 | 5 | 1 | 2 | 68.8% | [0.5, 0.875] |

Highest balanced-start winning setting: baseline 2400; candidate 2400. A single victory is not a stable rating. Small-sample intervals describe these opening pairs and do not cover opponent calibration or hardware differences.

Promotion: Fresh paired 95% lower score bound versus v1.14 did not exceed 50%.

## Held-out phase decisions

| Build / mode | Accepted | 200cp blunders | Mean regret cp | Median ms |
|---|---:|---:|---:|---:|
| classical-witty-magnus-v1 / clock4000:all | 63/96 | 5 | 66.32291666666667 | 555.5 |
| classical-witty-magnus-v1 / clock4000:opening | 18/24 | 1 | 58.583333333333336 | 559.0 |
| classical-witty-magnus-v1 / clock4000:middlegame | 15/24 | 1 | 71.66666666666667 | 645.9 |
| classical-witty-magnus-v1 / clock4000:transition | 11/24 | 1 | 82.54166666666667 | 600.9 |
| classical-witty-magnus-v1 / clock4000:endgame | 19/24 | 2 | 52.5 | 397.7 |
| classical-witty-magnus-v1 / clock800:all | 64/96 | 7 | 73.375 | 388.4 |
| classical-witty-magnus-v1 / clock800:opening | 19/24 | 1 | 54.5 | 392.6 |
| classical-witty-magnus-v1 / clock800:middlegame | 15/24 | 1 | 71.66666666666667 | 392.0 |
| classical-witty-magnus-v1 / clock800:transition | 11/24 | 3 | 114.83333333333333 | 392.0 |
| classical-witty-magnus-v1 / clock800:endgame | 19/24 | 2 | 52.5 | 272.6 |
| classical-witty-magnus-v1 / nodes2000:all | 63/96 | 5 | 66.8125 | 730.0 |
| classical-witty-magnus-v1 / nodes2000:opening | 17/24 | 1 | 61.083333333333336 | 893.8 |
| classical-witty-magnus-v1 / nodes2000:middlegame | 15/24 | 1 | 71.66666666666667 | 820.5 |
| classical-witty-magnus-v1 / nodes2000:transition | 12/24 | 1 | 82.0 | 657.3 |
| classical-witty-magnus-v1 / nodes2000:endgame | 19/24 | 2 | 52.5 | 544.6 |
| classical-witty-magnus-v1 / nodes2000_book_off:all | 63/96 | 5 | 66.8125 | 366.2 |
| classical-witty-magnus-v1 / nodes2000_book_off:opening | 17/24 | 1 | 61.083333333333336 | 409.0 |
| classical-witty-magnus-v1 / nodes2000_book_off:middlegame | 15/24 | 1 | 71.66666666666667 | 358.2 |
| classical-witty-magnus-v1 / nodes2000_book_off:transition | 12/24 | 1 | 82.0 | 371.1 |
| classical-witty-magnus-v1 / nodes2000_book_off:endgame | 19/24 | 2 | 52.5 | 297.2 |
| threephase-pvs-v1 / clock4000:all | 65/96 | 3 | 64.65625 | 532.6 |
| threephase-pvs-v1 / clock4000:opening | 15/24 | 1 | 69.79166666666667 | 528.8 |
| threephase-pvs-v1 / clock4000:middlegame | 16/24 | 0 | 54.541666666666664 | 575.3 |
| threephase-pvs-v1 / clock4000:transition | 12/24 | 2 | 109.16666666666667 | 562.8 |
| threephase-pvs-v1 / clock4000:endgame | 22/24 | 0 | 25.125 | 400.9 |
| threephase-pvs-v1 / clock800:all | 63/96 | 4 | 63.885416666666664 | 389.3 |
| threephase-pvs-v1 / clock800:opening | 16/24 | 1 | 70.125 | 392.2 |
| threephase-pvs-v1 / clock800:middlegame | 15/24 | 1 | 71.66666666666667 | 392.1 |
| threephase-pvs-v1 / clock800:transition | 12/24 | 1 | 82.0 | 392.0 |
| threephase-pvs-v1 / clock800:endgame | 20/24 | 1 | 31.75 | 270.5 |
| threephase-pvs-v1 / nodes2000:all | 64/96 | 5 | 66.92708333333333 | 258.0 |
| threephase-pvs-v1 / nodes2000:opening | 18/24 | 1 | 59.375 | 283.3 |
| threephase-pvs-v1 / nodes2000:middlegame | 15/24 | 1 | 73.83333333333333 | 259.7 |
| threephase-pvs-v1 / nodes2000:transition | 12/24 | 1 | 82.0 | 267.8 |
| threephase-pvs-v1 / nodes2000:endgame | 19/24 | 2 | 52.5 | 213.4 |
| threephase-pvs-v1 / nodes2000_book_off:all | 64/96 | 5 | 66.92708333333333 | 250.7 |
| threephase-pvs-v1 / nodes2000_book_off:opening | 18/24 | 1 | 59.375 | 279.7 |
| threephase-pvs-v1 / nodes2000_book_off:middlegame | 15/24 | 1 | 73.83333333333333 | 246.7 |
| threephase-pvs-v1 / nodes2000_book_off:transition | 12/24 | 1 | 82.0 | 269.8 |
| threephase-pvs-v1 / nodes2000_book_off:endgame | 19/24 | 2 | 52.5 | 215.0 |

The 96 test positions have 24 per phase. Modes reuse the same positions. Teacher estimates were verified at 80k/320k nodes, but remain finite-search estimates. The 192 diagnostic training positions did not fit weights. New whole-game/event/prefix grouping and exact/mirrored board exclusions reduce leakage; incomplete older source identities and semantic similarities remain limitations.

## Endgame drills

Advantageous KQK/KRK starts measure conversion; their wins do not count as defeating 2600 in ordinary games. Near-zero held-out endgames use finite teacher estimates and fresh repetition history at the recorded FEN, not tablebase certificates.

- classical-witty-magnus-v1: `{"basic_conversion": {"checkmate": 3, "not_converted:threefold_repetition": 1}, "practical_results": {"0.5": 2}}`
- threephase-pvs-v1: `{"basic_conversion": {"not_converted:threefold_repetition": 2, "checkmate": 2}, "practical_results": {"0.0": 1, "1.0": 1}}`

Terminations: `{"checkmate": 63, "threefold_repetition": 16, "fifty_moves": 1}`.

The public source ledger records supplied-source provenance separately from material inspected in this session. Raw historical scores, commercial texts and external engines are not runtime assets. All benchmark weights stayed fixed; game rewards were not used in this experiment. The separately requested elite-case learning experiment follows this frozen assessment.
