# Resumed competition development — 7 September 2026

The user resumed improvements and explicitly rejected long independent
consistency checks again. The work used existing actual-game mistakes and
small code gates; no new large match study or data download was started.

A full-window trace of round55 found that depth9 preferred Rc1 (+159cp)
over Kf1 (+25cp), but the ordinary root could not finish depth9 in12 seconds.
The teacher identifies the quiet Nb6 continuation after Rc1 Rxe2.
This motivated reducing useful calculation cost before another NN fit.

| Cycle | Change | Result |
|---|---|---|
| 10 | Conservative null-move pruning | Rejected: all11 errors repeated by both builds |
| 11 | Exact static evaluation cache | Exact parity; 1.0463x speed, below1.10 gate |
| 12 | Passed-pawn masks | Exact parity; 1.0052x speed, below1.10 gate |
| 13 | Sufficient legal-pawn proof | Exact parity=True; 1.5702x speed; gate passed=True |

Each exact-work gate used11 exposed roots at250k nodes, two alternating
passes per build. All outcomes were kept; no timing retries. The experiments
passed11,5,7 and9 respective correctness checks. They do not establish Elo.

The selected download remains v1.41 until a new package passes its runtime
checks and a short practical comparison. No live competition upload occurred.

Completed practical pair: **0 wins, 1 draw, 1 loss against v1.41**,120+0.5. All source, legal-move, clock and outcome audits passed; candidate runtime failures=0. Selected download: **v1.41**. This follows the declared practical rule and does not establish an Elo gain or stable superiority. v1.41 is retained.

Post-game feedback screened127 own moves and found3 stable200cp errors. The
loss first deteriorated in the middlegame (23.Ne1 versus Ne5), despite ending
in the endgame. The draw squandered a winning endgame with56...Bxe8, allowing
promotion; ...Rb7 retained the advantage. These cases now guide the next
bounded diagnosis. No repeated match pair or long study was started.
