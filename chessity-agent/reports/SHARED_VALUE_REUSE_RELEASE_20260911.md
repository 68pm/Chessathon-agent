# chessity-agent v1.57

The successor learns how to evaluate positions reached during search, using a shared piece embedding, king-location features and blocked-centre context. Queenless starting positions use the exact selected v1.56 search throughout the calculation, including imagined promotions. The searches keep separate state.

| Opponent | Wins | Draws | Losses |
|---|---:|---:|---:|
| Exact v1.56 | 5 | 1 | 0 |
| Stockfish nominal 2400 | 0 | 2 | 0 |
| Stockfish nominal 2600 | 1 | 0 | 1 |
| Stockfish nominal 2800 | 0 | 2 | 0 |

Highest nominal setting defeated: **2600**. These short 120s + 0.5s games do not establish calibrated Elo or a victory over the actual leaderboard leader.

On eight reserved games, 29 suitable positions reduced value error from 289.45 to 215.28cp; errors of at least 200cp fell from 17 to 10. Both colours improved. Those games were excluded from training and checkpoint selection.

The 27 exposed development tactical positions improved from 259.30/282.56cp regret to 170.94/190.31cp at 80k/320k teacher budgets, with no added major or mating losses. This diagnostic is separate from the fresh playing comparison.

Twenty-three compiled value/special-move checks, eight static-cache checks and four routing checks passed. Read-only validation used 40.45s initialization and 348.4MiB peak working set. Two legal calls passed; filesystem mutations, networking and subprocesses were blocked.

Every game was independently reviewed: 570 candidate moves, 372 positive and 29 corrective signals. Playing weights stayed frozen.

A finite six-opening pool was frozen before teacher labels or playing outcomes. All six passed balance checks; the predeclared first three were used for comparison, and the first for rated pairs, with colours swapped. These starting positions had not been scheduled in earlier local matches.

King-context reuse and a static-value cache achieved 1.107x CPU speedup against the same model using its earlier runtime, with identical fixed-depth moves, scores and nodes. This is not a speed comparison against classical v1.56.

Competition upload and validation remain pending at release preparation. All 57 earlier archives are preserved.

ZIP SHA256: `2e173cb2ccc5a8184e6546296730535d667e6d201ac44d843ad0d339630a786e`.
