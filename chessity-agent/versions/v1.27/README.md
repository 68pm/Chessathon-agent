# chessity-agent v1.27

Elite outcome-guided policy after training game 2. **validation retained previous checkpoint; identical ZIP to v1.26.**

The proposed update did not improve validation, so this chronological stage preserves the previous weights and identical ZIP.

Recommended competition upload remains v1.14. The original classical evaluator, clock control and optional Alien preference are preserved; the policy uses locally trained weights. No external engine or teacher lookup ships.

Archive: `chessity-agent-v1.27.zip`. SHA-256: `c1ba8a6b6ba5c496cca48bfa81c7ee6f3fb8095f56e26c5dcd112968e5eba011`. Source and weights in `source/` are byte-exact archive contents. Three read-only smoke calls passed.

See [the completed learning report](../../reports/ELITE_LEARNING_RESULTS.md). Nominal Stockfish settings are not a human/site rating.
