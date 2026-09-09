# Faster search retained as a component, not a selected release

The fast-legal-01 screen completed at 12:12 BST on 9 September. All eight games
used 120s + 0.5s and frozen playing weights, with both colours in each pair.

| Opponent | Wins | Draws | Losses |
|---|---:|---:|---:|
| Exact v1.55 | 0 | 2 | 0 |
| Exact v1.53 | 1 | 1 | 0 |
| Stockfish nominal 2400 | 1 | 1 | 0 |
| Stockfish nominal 2600 | 0 | 0 | 2 |

No 2800 games were authorised by the conditional advancement gate. All 434
candidate moves were reviewed: 253 positive and 24 negative signals, with 17
middlegame and seven endgame corrections. There were no operational failures.
Post-game policy fits remained experimental and did not alter the playing model.

The candidate failed the predeclared direct v1.55 comparison requirement. Its
favourable 2400 pair did not extend to 2600. Preserve the 15% measured fixed-work
speed gain for future development, but retain selected v1.55 and its existing ZIP.
This candidate was not numbered, published as a release, or uploaded to Chessathon.
No calibrated Elo follows from these small development samples.

The 2600 White loss started with smaller middlegame concessions and later weak
rook-ending choices. Black again weakened its king with 13...f6: both teacher
budgets found a large loss, but disagreed on the best replacement, so no single
policy target was invented. Later checking moves and material grabs did not repair
the defence. Treat earlier recoverable positions as the main engineering targets.

The subsequent five-position probe tested exact selected v1.55 at one and three
seconds with full histories. It still missed all four own-game turning points:
...Kg7 in round 77, the two Bxh7+ opportunities and Ng5 in round 78. These reached
depths six and seven, with depth eight unfinished. At the longer budget their
teacher regrets were respectively 289, 166, 278 and 297cp. It already found ...Kg7
in the leader's queen-ending position at both budgets, with zero teacher regret.

The probe was diagnostic: ten searches, no training or model mutation. The
student process closed before independent teacher review; only 400000 new teacher
nodes were requested because matching cached evaluations were reused. Source
hashes, board histories and complete per-depth choices are preserved in
field-selected-probe-01. This distinguishes present defects from unknown older
public submissions without falsely identifying which ZIP played those public games.
