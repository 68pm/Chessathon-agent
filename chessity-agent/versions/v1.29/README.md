# chessity-agent v1.29

Elite outcome-guided policy after training game 4. **validation retained previous checkpoint; identical ZIP to v1.28.**

The proposed update did not improve validation, so this chronological stage preserves the previous weights and identical ZIP.

Recommended competition upload remains v1.14. The original classical evaluator, clock control and optional Alien preference are preserved; the policy uses locally trained weights. No external engine or teacher lookup ships.

Archive: `chessity-agent-v1.29.zip`. SHA-256: `ade796d9badefcb50d6b22ca545532f2109708659ff7129b362201a600113950`. Source and weights in `source/` are byte-exact archive contents. Three read-only smoke calls passed.

See [the completed learning report](../../reports/ELITE_LEARNING_RESULTS.md). Nominal Stockfish settings are not a human/site rating.
