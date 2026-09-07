# Current selected agent: chessity-agent v1.41

**Recommended competition upload: v1.41.** The exact ZIP is available through the latest download. It passed the predeclared independent promotion rule over v1.14. The continuing 2600 programme remains active.

| Opponent | Wins | Draws | Losses |
|---|---:|---:|---:|
| v1.14 | 23 | 1 | 0 |
| stockfish:2400 | 3 | 4 | 1 |
| stockfish:2600 | 0 | 3 | 5 |

All 40 games used 120+0.5 and passed legal-move, clock, increment, outcome and frozen-source audits, without runtime failures. The comparison used 12 distinct paired starting groups; the rated tests used 4 further groups in both colours. The conservative comparison score lower bound was 58.7%, above 50%, with attempt-adjusted alpha 0.025. It assumes independent groups and stable conditions.

Highest nominal setting defeated in this set: **2400**. These Stockfish handicap numbers are not calibrated Chess.com/FIDE ratings. This sample does not establish consistent 2600 wins or the strongest possible engine. Earlier development and failed experiments remain visible; no games were added to chase a win.

The improvement comes from our original compiled search, faster quiescence terminal checks and exact elementary endgame tables. It preserves the previously trained Classical/Witty/Magnus root policy and bounded optional Alien preference. The new residual network did not demonstrate a matched playing-strength gain and was not merged into the selected runtime.

Strict read-only/no-network/no-subprocess inference passed, including table probes. Initialization was 28.80s and peak measured memory 229.6MB. Only original Python source and own weights plus attributed permitted table data ship; compilation occurs in memory. The prior full suite passed 108 tests, and four additional successor-data tests passed separately.

ZIP SHA-256: `e4b66bd0f5a16418a49119c0547a818c3bb79a3c9e209b3eca7210907e072f63`. All 42 historical versions through v1.41 remain available. No competition upload or repository write-access grant was performed.

Next: analyse the rated games and verify played-versus-preferred successor targets before another bounded learning experiment. Once used for development, these rated opening groups must not be reused as fresh confirmation. The full-project backup is refreshed separately.
