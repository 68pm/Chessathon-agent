# v1.53 rated screen: no rated opponent defeated

The four declared **120s + 0.5s** games are complete. The opponent ratings below
are local Stockfish handicap settings, not calibrated human or competition Elo.

| Opponent setting | Wins | Draws | Losses |
|---|---:|---:|---:|
| 2400 | 0 | 1 | 1 |
| 2600 | 0 | 0 | 2 |

The White2400 game drew by threefold repetition. All three losses ended by
checkmate. There were no candidate or opponent clock, startup, crash or illegal
move failures. Every move, both clocks, source hashes and the four-game schedule
were audited. Candidate initialization was69.82/51.65/51.25/45.94 seconds.
The single E90 opening pair at each setting is too small to estimate Elo or
establish a strength difference from another version tested on another opening.

The highest opponent this exact build has defeated remains **Chessity v1.52**,
whose Elo is uncalibrated. Older nominal2600 wins are not v1.53 results. v1.53
remains a provisional practical recommendation under its original tactical and
two-game selection rules; this screen supplies no evidence of2400 strength.

All160 candidate moves were screened at20k teacher nodes and suspicious choices
verified at80k/320k. Seven finite errors exceeded200cp at both budgets;17
mate-scored rows are retained separately. The review requested33.3million nodes
within the134.4million maximum. Phase analysis reused the labels without new
teacher work. No games, neural fits or playing-code changes were added.

| Game | First verified warning | Regret at80k /320k | Stage |
|---|---|---|---|
| White vs2400, draw | 28.f4; alternatives Nd1 / Nb1 | 128 /109cp | Endgame |
| Black vs2400, loss | 10...Nc6 instead of Kh7 | 424 /404cp | Opening |
| White vs2600, loss | 14.Qb3 instead of h3 | 261 /286cp | Middlegame |
| Black vs2600, loss | 15...Na3 instead of Qc5 | 207 /214cp | Middlegame |

The Black2600 game's first stable transition to a losing position came later,
at19...Bh4 instead of Be6, costing285/423cp. The draw's warning is a smaller
losing transition, not a200cp blunder. Both alternative knight moves in that
draw are retained because the teacher budgets disagree. Terminal stages were
middlegame/endgame/middlegame for the three losses, using the unchanged material
definition. A first warning is not proof of the entire cause of a loss.

Engine work should next examine the missed defensive continuations, particularly
why the opening king escape and h3 defence were undervalued. Useful learning
needs independent values for the actual descendants reached by both sides;
fitting a favorable imagined line alone can reinforce the wrong decision.
These recent games provide targeted examples. There is no reason to add broad
game collections or repeat unchanged training epochs before that diagnosis.

The selected ZIP, weights and all54 numbered archives are unchanged. No long
consistency study, repository permission changes or live competition upload.

[Original screen rules](NEAR_QUEEN_RATED_20260908.md) ·
[Review rules](NEAR_QUEEN_RATED_REVIEW_20260908.md) ·
[Raw games and evidence](evidence/near-queen-rated-20260908/manifest.json)
