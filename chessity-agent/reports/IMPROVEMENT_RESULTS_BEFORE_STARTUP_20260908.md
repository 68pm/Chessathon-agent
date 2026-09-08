# Current selected agent: chessity-agent v1.41

**Recommended competition upload: v1.41.** The latest ZIP and versioned download match.

Newest archived build: **v1.49**, the queen-aware passed-pawn candidate. Its
ten-game test scored0W/0D/2L versus41,0W/2D/0L versus47,1W/0D/1L versus48,
0W/0D/2L at2400 (both startup failures), and1W/1D/0L at2600 (win by opponent flag).
It is not recommended. [Full results and diagnosis](COMPETITION_TEN_GAME_REVIEW.md).

The user-requested [mistake-replay pilot](IMPROVEMENT_CYCLE_16.md) also completed:
three rounds changed the trained-position success count from1/7 to0/7,3/7 and2/7.
The final candidate failed the separate held-out check against its matched control;
its checkpoints are preserved as training experiments, not promoted releases.

v1.48 changes only the stalemate-existence guard: a sufficient legal-pawn proof
can avoid generating a complete pseudo-legal list. The existing trained
Classical/Witty/Magnus policy, optional Alien preparation, evaluation and
elementary tables are preserved. No new neural training was claimed.

The predeclared short comparison against v1.41 scored **0W/1D/1L**
at120+0.5, one starting position in both colours. Every result was kept and
all legal/clock/source/outcome audits passed; candidate failures=0.
It did not meet the practical selection rule; retain v1.41.
Two games do not establish higher Elo or stable winning superiority.

Nine correctness checks and44 fixed-work search measurements passed. Scores,
moves, depths and node counts were identical. Both timing passes were faster,
but host timing varied: aggregate1.5702x, smaller paired gain about1.24x.
Do not interpret these figures as guaranteed competition-server performance.

The v1.48 read-only check passed: import21.831s, peak234.1MB, two legal calls
at120000ms, maximum move3.485s. Filesystem mutations, network and subprocess
were blocked. ZIP272622 bytes;328348 bytes uncompressed.

Selected ZIP SHA256: `e4b66bd0f5a16418a49119c0547a818c3bb79a3c9e209b3eca7210907e072f63`. All50 chronological versions
throughv1.49 are retained. No live competition upload or write-access grant.

## Separate historical v1.41 results

| Test | Wins | Draws | Losses |
|---|---:|---:|---:|
| Confirmation vs v1.14 | 23 | 1 | 0 |
| Confirmation, nominal2400 | 3 | 4 | 1 |
| Confirmation, nominal2600 | 0 | 3 | 5 |
| Later short check, nominal2400 | 0 | 0 | 2 |
| Later short check, nominal2600 | 1 | 0 | 1 |
| Competition rounds54–56 (v1.41 inferred) | 2 | 1 | 0 |

These are separate datasets. Older models played most earlier dashboard games.
v1.48 has not yet played a nominal2400/2600 match. Do not transfer v1.41 results
to v1.48 or convert handicap settings into a calibrated human/site rating.
The long independent consistency study remains abandoned.

[Previous detailed history](IMPROVEMENT_RESULTS_V1_41_HISTORY.md) ·
[Latest development findings](COMPETITION_DEVELOPMENT_UPDATE.md) ·
[Actual competition games](COMPETITION_RECENT_GAMES.md)
