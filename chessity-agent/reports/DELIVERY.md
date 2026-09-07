# chessity-agent delivery — 7 September 2026

This is the historical phase/elite delivery. **The current selected agent is v1.41**;
see [the newer confirmation results and download](IMPROVEMENT_RESULTS.md).

**Recommended competition upload: v1.14.** The new phase-search and elite-learning candidates did not pass the frozen promotion rules. Upload `../chessity-agent.zip` directly. Newest experimental build: v1.34, the teacher-only control; the final outcome-trained candidate is v1.33.

- [Recommended ZIP on GitHub](https://github.com/68pm/Chessathon-agent/raw/refs/heads/main/chessity-agent/latest/chessity-agent.zip)
- [All 35 versions in development order](https://github.com/68pm/Chessathon-agent/tree/main/chessity-agent)
- [Completed elite learning, rewards and per-game review](ELITE_LEARNING_RESULTS.md)
- [Completed three-phase search experiment](THREEPHASE_RESULTS.md)
- [Earlier delivery and dated results](DELIVERY_20260906.md)

## Actual results at 120 seconds plus 0.5 seconds

| Build | Nominal Stockfish setting | Wins | Draws | Losses |
|---|---:|---:|---:|---:|
| Selected v1.14, fresh baseline | 2200 | 1 | 0 | 3 |
| Selected v1.14, fresh baseline | 2400 | 1 | 1 | 2 |
| Selected v1.14, fresh baseline | 2600 | 0 | 0 | 4 |
| v1.24 PVS experiment | 2200 | 1 | 1 | 10 |
| v1.24 PVS experiment | 2400 | 2 | 0 | 10 |
| v1.24 PVS experiment | 2600 | 0 | 3 | 9 |
| v1.33 outcome-trained candidate | 2400 | 1 | 1 | 14 |
| v1.33 outcome-trained candidate | 2600 | 0 | 5 | 11 |

Highest individual winning setting: **2400**. No ordinary-game win against 2600 occurred, and neither consistency target was met. These are nominal engine settings, not a calibrated human/site Elo. Different test sample sizes/opening sets limit comparisons across stages; direct paired games drive selection.

The final outcome candidate scored 5W/2D/9L against v1.14 and 3W/1D/4L against its matched teacher-only ablation. The PVS candidate scored 4W/7D/5L against v1.14 in fresh confirmation. Both failed promotion.

## What actually learned

The supplied elite Markdown contained 21 distinct cases from 20 games; 20 passed independent 80k/320k-node checks and one was quarantined. The referenced 1,862-game corpus was unavailable and was not used. The existing policy was fitted with those cases plus prior train-only Carlsen/Witty, puzzle and phase replay. Raw training-case recognition improved from 16/20 acceptable moves to 18/20, but fresh matches did not establish a strength gain.

Eight adaptation games produced 0 wins, 2 draws and 6 losses. All 715 recorded plies were submitted for Stockfish review; 542 were verified, including 261 own moves. Teacher corrections informed each subsequent training attempt. The outcome rule adds a bounded bonus only for a sound move from a win or draw. It reinforced 77 distinct sampled drawing choices and zero winning choices, because the adaptation games contained no wins. This is outcome-guided supervised training, not policy-gradient RL. Final evaluation weights stayed fixed.

The 92 phase games and 64 elite games passed legal-move, clock, increment, result and source audits. Endgame advantage drills are excluded from highest-rated-win claims. The selected ZIP passed read-only checks; no file mutations, network or subprocess are needed at inference. Exact SHA-256: `6d287209c28bba520a21ef49261af99543a167fb192ce15513102c883c503a56`.

All versions are retained chronologically. v1.27 equals v1.26 and v1.29 equals v1.28 because those updates were rejected by validation. Public versions contain own source/weights and measured reports; raw third-party histories, supplied source packs and external engines are excluded. The local development backup retains the supplied material and training evidence. No competition upload or repository write-access grant was performed.
