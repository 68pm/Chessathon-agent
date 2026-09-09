# Recommended upload: chessity-agent v1.55

The new pawn evaluator preserves exact classical scores while reducing repeated
passed-pawn scanning. Twelve development roots gave an aggregate CPU speedup
of 1.15108 and median 1.15783, with identical 250000-node moves, scores and depths.
Clock-choice teacher review found no new major mistakes or mate losses.

| Opponent | Wins | Draws | Losses |
|---|---:|---:|---:|
| Exact v1.54 | 2 | 0 | 0 |
| Exact v1.53 | 2 | 0 | 0 |
| Stockfish nominal 2400 | 0 | 0 | 2 |
| Stockfish nominal 2600 | 1 | 1 | 0 |
| Stockfish nominal 2800 | 0 | 1 | 1 |

Highest clean nominal setting defeated in this screen: **2600**.
These are short development tests at 120s + 0.5s, using both colours. They do not
establish calibrated Elo or consistent superiority over a nominal rating.

All 430 candidate moves were reviewed; independent Stockfish
labels supported 214 moves and identified 31 corrections.
Post-game policy fits are experimental and did not change the playing weights.
The uploaded source retains v1.54's learned root policy and classical searched-
position evaluation. Rejected value fits are absent; the signed-output learner
remains a separate development experiment. Quiet defensive moves and endgame
conversion remain useful improvement targets, including misses in won games.

The two losses at 2400 were worse than the previous release's earlier draw
and loss in that setting. The new version won the direct archive comparisons
and scored a clean 2600 win, but these small samples remain variable. Its
2600 draw also included an engine-supported missed mate for the opponent;
king defence is still an unresolved weakness.

Strict read-only validation passed: 18.226s startup
against 90s, two legal move calls, blocked filesystem mutations, no network or
subprocess use in inference. Local timing does not guarantee site validation.

ZIP SHA256: `29b322dba4ea61d0fce1709327810e8f9f199df79cf40cc92290ddf9ec083fc1`. All 55 older ZIPs remain byte-identical.
The user authorised automatic competition submission; browser control remains
unavailable due a kernel-assets missing-path error. No successful site upload
or new active submission has yet been observed.
