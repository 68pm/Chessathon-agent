# Defensive alternatives: search-depth and value diagnosis

The new public-game batch is complete: our round76 win and the current leader
stockfih's rounds77/76/75 (loss/win/win). All249 moves by the relevant agents were
reviewed:160 positive signals and11 corrections. Our50moves included26positive
signals and8middlegame corrections. The three leader games supplied199moves,
134positive signals and3endgame corrections. Neither team's submission hashes
are public in this evidence, so none is attributed to a particular Chessity ZIP.
Experimental policy fits remain separate and unselected.

The trace uses exact selectedv1.54 on eight exposed positions, both with and
without late-move reductions. Each cold-table call retains full history and the
existing root policy. There are48calls: all root choices, the played move forced,
and the independently preferred defensive move forced, in each reduction mode.
Forced branches are diagnostic engine searches, never fresh teacher labels.

Every whole-root call hit the500,000-node diagnostic cap in0.74–1.16seconds,
before the2.5second ceiling. These are fixed-work diagnostics, not reproductions
of an entire competition move budget or retained transposition state. All source
files and input boards remained unchanged. No new compiler signatures appeared.
Initialization took18.870seconds.

With reductions enabled, representative depth7 forced-branch scores were:

| Position | Played branch | Preferred branch | Student scores (cp) | Deep teacher scores (cp) |
|---|---|---|---|---|
| 2400 loss, White24 | Nh3 | Nxf7 | +3 / -27 | -449 / -142 |
| 2600 loss, Black23 | h2 | Qg7 | +219 / +30 | -396 / -194 |
| Public win, Black44 | Rxa2 | Qa5 | +362 / +258 | +537 / +650 |

The engine can search the defensive alternatives and still prefer the inferior
branch. Disabling reductions did not repair these comparisons at their common
completed depths. It usually reduced whole-root depth by one under the same
node cap. It improved the exact choice on two other roots and worsened another,
so neither blanket removal nor an ordering-only explanation is justified.

The next efficiency experiment keeps reductions and all chess values unchanged:
scalar per-evaluation pawn masks and bishop/material counters on v1.54. Any
remaining value-learning targets need independently checked descendant values.
The older all-positive-output fit and the new signed-head fit remain rejected.
Do not assign a root Stockfish score to a student leaf or assume every raw
tablebase win survives the current fifty-move clock.

The first trace attempt failed during import, before any engine search, because
capacity helpers had loaded the project's other engine package. The separate
second attempt explicitly isolated the candidate package and completed. Both
attempts and their supervisor logs remain intact. This is diagnostic evidence,
not new playing results or a rating estimate.
