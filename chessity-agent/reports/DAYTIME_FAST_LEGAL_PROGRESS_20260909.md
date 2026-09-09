# First six reviewed games of the fast legal-existence candidate

At 12:03 BST on 9 September, the first three pairs were complete. The nominal
2600 pair was running. These are provisional screen results, not a release decision.

| Opponent | Wins | Draws | Losses |
|---|---:|---:|---:|
| Exact v1.55 | 0 | 2 | 0 |
| Exact v1.53 | 1 | 1 | 0 |
| Nominal 2400 | 1 | 1 | 0 |

All 286 candidate moves in these pairs were reviewed: 199 positive signals and
15 negative signals, of which ten were middlegame and five endgame corrections.
The playing weights remained frozen. Post-game policy fits remain unselected.

The direct v1.55 comparison has not met the predeclared 1.5/2 requirement. Do not
relax that gate because the rated 2400 result is encouraging. Finish the declared
rated screen and retain the selected release unless a separately justified new
candidate qualifies. Preserve this faster component for further engineering work.

Both draws against v1.55 ended in positions assessed approximately equal by both
teacher budgets. The final repetitions are not supported evidence of throwing
away a win. Earlier errors matter more: White 15.Nfd4 instead of Be3 was about a
four-pawn evaluation loss, and Black 25...Ne5 instead of ...Nd4 lost about two
pawns of evaluation. Forcing the engine to refuse all draws would not repair those
earlier mistakes and could turn saved games into losses.

The nominal 2400 White win had one stable inaccuracy: 20.Rc5 instead of Ng5, while
still retaining a large advantage. Black's long draw contained 15...f6, a major
king-defence error compared with the quiet ...Ra7. The teacher's larger-budget
values were -49cp for its best move and -302cp after ...f6. This repeats the general
need to examine quiet defensive moves before weakening the pawn shield, even in
a game the candidate eventually saved.

The existing full-history five-position public probe remains queued until the
screen closes. Inspect current failures before extending training. Code inspection
also found a potential ordering improvement: the search currently ignores a stored
move when the board matches but the repetition context differs. Reusing only the
move as an ordering hint may be safe while retaining all history and halfmove
guards for cached scores. This is a proposed isolated experiment, not implemented,
measured or selected. Any trial needs guard tests and tactical quality checks.
