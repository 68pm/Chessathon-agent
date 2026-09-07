# chessity-agent v1.33

Elite outcome-guided policy after training game 8. **final outcome candidate; not promoted after fresh comparisons.**

Fresh results: 5W/2D/9L versus v1.14, 3W/1D/4L versus the teacher-only control, 1W/1D/14L at 2400 and 0W/5D/11L at 2600.

Recommended competition upload remains v1.14. The original classical evaluator, clock control and optional Alien preference are preserved; the policy uses locally trained weights. No external engine or teacher lookup ships.

Archive: `chessity-agent-v1.33.zip`. SHA-256: `0b2f5898752a504f9e2c3e9f715c9e44654e097759b94878d95919782d39b677`. Source and weights in `source/` are byte-exact archive contents. Three read-only smoke calls passed.

See [the completed learning report](../../reports/ELITE_LEARNING_RESULTS.md). Nominal Stockfish settings are not a human/site rating.
