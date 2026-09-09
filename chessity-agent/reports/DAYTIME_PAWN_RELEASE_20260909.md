# Recommended upload: chessity-agent v1.54

The new pawn evaluator preserves exact classical scores while reducing repeated
passed-pawn scanning. Twenty development roots gave an aggregate CPU speedup
of1.05605 and median1.05806, with identical250000-node moves, scores and depths.
Clock-choice teacher review found no new major mistakes or mate losses.

| Opponent | Wins | Draws | Losses |
|---|---:|---:|---:|
| Exact v1.42 | 2 | 0 | 0 |
| Exact v1.53 | 1 | 1 | 0 |
| Stockfish nominal 2400 | 0 | 1 | 1 |
| Stockfish nominal 2600 | 0 | 1 | 1 |

No rated-setting win was recorded in this screen.
These are short development tests at120s+0.5s, using both colours. They do not
establish calibrated Elo or consistent superiority over a nominal rating.

All 438 candidate moves were reviewed; independent Stockfish
labels supported 261 moves and identified 25 corrections.
Post-game policy fits are experimental and did not change the playing weights.
The uploaded source retains v1.42's learned root policy and classical searched-
position evaluation. Rejected value fits are absent; the signed-output learner
remains a separate development experiment. Quiet defensive moves and endgame
conversion remain useful improvement targets, including misses in won games.

Strict read-only validation passed: 18.565s startup
against90s, two legal move calls, blocked filesystem mutations, no network or
subprocess use in inference. Local timing does not guarantee site validation.

ZIP SHA256: `9c5707d4dc4aa918ecb01ba284f9dd4f7469b22d50afd4b6a6d425e6f44c585e`. All54older ZIPs remain byte-identical.
The user authorised automatic competition submission; browser control remains
unavailable due a kernel-assets missing-path error. No successful site upload
or new active submission has yet been observed.
