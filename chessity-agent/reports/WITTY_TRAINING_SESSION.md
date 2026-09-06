# Player-style training completed — 6 September 2026

Downloaded **166,438 unique available games** across 129 monthly
archives, saved as 3,329 parts of at most 50 games. There were
952 missing PGNs and 0 duplicate records.
All 952 bughouse records without PGN are retained
in the raw JSON and excluded from standard-chess move training.
The user confirmed written Chess.com authorisation in this task before collection.
Only completed games exposed by the public index at collection time are covered;
private, deleted, unexposed and later games are outside this snapshot.

## What was trained

The original 300,000-position value-training run was already complete. Its self-trained
value weights are retained. This session trained a separate original 935–64–32–1
move-ranking neural network on **50,000 recorded Witty_Alien decisions**, sampled
across the entire history. Split counts: 40,015 training,
4,981 validation and 5,004 test.
These are positions/decisions, **not 300,000 self-play games**.

Each training target is his actual legal move against up to four sampled legal alternatives.
Checks/captures are prioritised within each game; the sample reserves the exact Alien
sacrifice position when available. Whole-game hashes set the splits before sampling;
the final sample contains no repeated exact normalised FEN. Related positions can
remain across splits. Synthetic downloader fixtures were not used for training.

Completed 6 epochs, selecting epoch 3 using validation
cross-entropy only. On 1,000 held-out positions evaluated against
**all legal moves**, the policy matched his recorded move 43.0% of
the time (uniform legal choice: 5.7%), with top-three agreement
68.7%. This measures imitation, not strength or tactical soundness.
On those test positions the raw policy chose checks 23.3%
and captures 61.4% of the time, versus
19.5% and 43.1%
for the recorded player moves. This shows a forcing-move bias in the raw policy;
the final engine still evaluates those moves through search.

The policy adds at most 20 centipawns to root-search preferences in roughly balanced
middlegames. It is disabled in check, under 50 ms of search time, in late endgames and
when the classical evaluation exceeds three pawns. This is a limit at the current
search horizon, not a guarantee against future blunders. Proven mate scores are not
modified. The Alien Gambit remains an explicit prepared repertoire; its inclusion is
separate from learning broader move preferences.

## Observed history

Analysed 164,388 matching standard-chess games. Check frequency was
10.50 per 100 moves; capture frequency was
24.58. Exact Alien Gambit detection found
2,863 Nxf7 sacrifices in 2,881
opportunities. Counts accept Nd2/Nc3 transposition but do not cover every related gambit.
These descriptive counts do not establish that sacrifices are objectively sound.

## Fresh match results and estimated Elo

At 3 seconds + 0.05 seconds per move, the new candidate scored
**2 wins / 8 draws / 2 losses**
against the previous 300k hybrid in 12 games with colours reversed across six openings.
Observed checks per 100 moves were 7.18 for the
new candidate and 8.51 for the baseline.
This small sample does not establish a stable style change or justify promotion.

In a separate controlled check on 64 held-out positions at
equal completed search depth two, the policy changed 8 moves.
Baseline/policy check counts were 8/8,
capture counts were 23/24,
and matches to the player's recorded choice were
22/23.
The repertoire was disabled for this check. These small differences show that the
policy influences search, but do not establish a consistent increase in aggression.

The external benchmark completed **3 wins / 2 draws /
7 losses** in 12 games at **30 seconds + 0.3 seconds per move** against
Stockfish 19 handicap settings 1320, 1500 and 1700, four games per setting. There were no
illegal-move, crash or clock failures. The fitted estimate is
**1363 on that nominal handicap scale**, with a broad approximate
band of **1000 to 1700**. This is **not a Chess.com, Lichess, FIDE or official Chessathon rating**.

The band combines a colour-pair bootstrap stratified by opponent setting and a
conservative score interval, rounded outward to 100 points. It is a small-sample
approximation, not guaranteed coverage, and excludes calibration and hardware error.
Stockfish documents its handicap calibration at 120+1, different from these clocks.
The opening schedule and one opponent family also limit generalisation.
The results do not establish a strength gain or a consistent increase in attacking
play. The previous 1731 estimate came from a separate small match batch; its difference
from this estimate is not a controlled measurement of a rating change.

## Use the trained candidate

Run `Play-Trained-Aggressive.ps1`. The engine plays White with the learned policy and
Alien repertoire. Its portable runtime is `candidates/witty-300k-hybrid-v1.zip`.
The classical competition champion remains preserved. No third-party engine binary,
published neural weights or downloaded game history is in the candidate runtime.

All history is under `data/witty_alien-history/`; `latest.json` identifies the exact
snapshot. Training checkpoints, optimiser state, logs and full match evidence are under
`runs/witty-style-20260906/`. Compact audited evidence is in
`docs/evidence/witty-training-session.json`, with full PGNs alongside it.

Sources: [Chess.com public archive API](https://www.chess.com/news/view/published-data-api),
[Stockfish handicap documentation](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-Protocol-and-Stockfish-Commands.html),
[CC0 value-training data](https://database.lichess.org/).
