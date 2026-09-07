# Fixed-strength and phase diagnosis

User direction, 7 September 2026: build consistent wins at a fixed strength, locate
the level with no wins, and diagnose where the game first deteriorates. Review
engine code first, learning second and targeted data third in every iteration.

Keep the already-running v1.47 schedule unchanged. After it finishes, focus the
next development screens on nominal2400 plus the selected incumbent. The selected
v1.41 has3 wins in8 nominal2400 games and0 in8 nominal2600 games in its completed
confirmation: neither is consistent winning performance. Do not raise the opponent
setting following an isolated win. Revisit2600 after supported progress at2400,
using fixed schedules and both colours. A small screening improvement may justify
larger independent repeatability tests; it does not itself establish consistency.
Declare each future match budget and promotion rule before running the games.

The user subsequently specified the pool progression: once consistent wins against
2400 are verified, remove2400 from the regular pool and add2800. Similarly replace
2600 with3000 once verified. The pool is tracked in
configs/improvement-opponent-pool.json; neither initial level has qualified. The
installed offline opponent supports all four requested settings (UCI_Elo1320–3190).
Qualification uses two independent64-game blocks with the same frozen build,
both colours, fresh groups, an outright-win majority and a conservative lower bound
above50% in each block. Split an attempt-adjusted alpha budget across the blocks;
record unsuccessful attempts too. This larger cost is incurred only after promising
fixed development screens. Source, clock, outcome and freshness audits are required.
scripts/improvement_consistency.py implements the statistical component; it cannot
certify freshness or change the pool by itself. Two tests passed for small/drawn
screens, repeated groups, mixed candidates, runtime failures and stricter bounds
on later attempts. Record the attempt before starting either block, including an
unsuccessful attempt in the cumulative alpha allocation.
Higher settings remain nominal engine handicaps. No further replacement above3000
has been specified. Reaching2600 remains a reportable milestone, followed by the
user-authorised pool progression rather than an automatic pause before those checks.

Diagnosis budget, declared before aggregation: no new teacher calls or fitting.
Reuse complete move audits for v1.41's rated confirmation, v1.46's rated screen and
its comparison against v1.41. Analyse v1.47's rated screen after its existing audit
completes. Keep each candidate/opponent result separate. Every counted audit row
must match its source game's exact move, colour, position, history and score.

Operational phase definitions, fixed before counting: material phase is1 per knight
or bishop,2 per rook and4 per queen across both sides (initial total24). A position
with phase<=8 is endgame, irrespective of move number. Otherwise full moves1–12 are
opening and later moves are middlegame. Report the move number and material phase
alongside examples; these useful boundaries are not universal chess definitions.

Record the terminal phase separately from the first verified warning in lost games:
- Large finite error: the played move loses at least200cp versus the teacher's
  preferred move at BOTH existing80k/320k verification budgets.
- Losing transition: at both budgets the preferred move is above-200cp (or has a
  positive mate score) while the played move is at most-200cp (or negative mate),
  with at least80cp deterioration whenever both scores are finite.
- Mate-loss transition: the played move has a negative mate score at both budgets
  while the preferred move does not. Preserve this separately from centipawn gaps;
  a position already evaluated as lost is not a new competitive-to-losing transition.
- Squandered advantage: the preferred move is at least+200cp (or positive mate)
  while the played move is at most+100cp (or negative mate), at both budgets.

The first warning is the earliest large error, losing transition or mate-loss
transition. Also report the earliest losing transition separately. A warning is
evidence of deterioration, not proof that it caused the ultimate result. Retain
all losses with no identified warning as unresolved. Mate-scored or unstable rows
remain visible and are never converted to zero-error examples. Give per-phase move
exposure and verified-error counts; raw counts from unequal phases/games are not
a causal comparison. The20k screening pass can miss errors, so this is not an
exhaustive blunder census. Mark every source as exposed development evidence.

Training candidates are references to the first verified warnings and squandered
advantages in lost/drawn games, with full history, verified alternatives and phase.
They are a queue for review and independent successor verification, not newly
accepted labels or an automatic training set. Existing partition, collision and
teacher-stability rules still apply. Use the diagnosis to choose whether a code
repair or a better learning target is warranted before fetching external material.

## Initial measured result

Reused32 completed games and1,614 audited own moves with no new teacher nodes.
Source positions, full history, move, colour, game outcome and clock all matched.
Four tests cover phase boundaries, already-lost positions, mate/unstable scores and
the distinction between an early warning and a later endgame finish. All passed.

Lost games, classified by the first verified warning:

| Agent / opponent | Losses | Opening | Middlegame | Endgame | Unresolved |
|---|---:|---:|---:|---:|---:|
| v1.41 / nominal2400 | 1 | 0 | 1 | 0 | 0 |
| v1.41 / nominal2600 | 5 | 0 | 2 | 1 | 2 |
| v1.46 / nominal2400 | 2 | 0 | 2 | 0 | 0 |
| v1.46 / nominal2600 | 2 | 1 | 1 | 0 | 0 |
| v1.46 / v1.41 | 5 | 1 | 2 | 1 | 1 |

For v1.41 against2600, four of five losses ended in the endgame, but the first
verified losing transition was middlegame in two, endgame in one and unresolved
in two. Its sole2400 loss first crossed the losing threshold in the middlegame.
One drawn2400 game showed a squandered middlegame advantage; one drawn2600 game
showed a squandered endgame advantage. These are finite teacher estimates, not
proofs that those moves alone determined the outcome.

Only24 opening own moves were observed in v1.41's rated confirmation, because the
games began from supplied setups. Zero verified large opening errors in that set
does not establish a strong opening repertoire. Keep phase exposure, uncertain
mate-scored decisions and unresolved games visible. Do not combine versions into
one strength claim or infer that later endgame errors are the only weakness.

Twenty references to first warnings and squandered advantages are queued for review
across the three reports; they are not20 newly accepted or necessarily independent
training examples. Current engineering priority remains useful threat calculation
and reliable conversion. Learning/data changes follow diagnosis and successor
verification. v1.47's same report is queued after its frozen rated audit completes.
