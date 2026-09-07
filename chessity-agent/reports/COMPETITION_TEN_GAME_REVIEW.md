**Completed ten-game review: queen-pawn candidate, archived as v1.49**

The recommended upload remains **v1.41**. The new candidate did not justify a
switch: it lost both games against v1.41 and failed to initialize in both2400 games.
The schedule finished on7 September2026 at20:40:43UTC, including all post-game
audits. Every result is retained. No replacement games or long consistency check
were added.

| Opponent | Wins | Draws | Losses | What happened |
|---|---:|---:|---:|---|
| v1.41 | 0 | 0 | 2 | Both checkmate losses |
| v1.47 | 0 | 2 | 0 | Both threefold-repetition draws |
| v1.48 | 1 | 0 | 1 | One checkmate win and one checkmate loss |
| Stockfish19, nominal2400 | 0 | 0 | 2 | Both candidate initialization failures; no chess moves played |
| Stockfish19, nominal2600 | 1 | 1 | 0 | Opponent clock flag and a threefold-repetition draw |

Total:2W/3D/5L. The2600 win was on time, not checkmate or proof of stronger position
play. No agent Elo estimate follows from this one-opening diagnostic. All five
opponents used the same A39 English starting position with colours reversed,
120seconds plus0.5seconds per move, at most two simultaneous games.

Frozen candidate ZIP SHA256:
`a1cd0bea47752ecec5774ce1d9adeeb05a9147948006e2a1c1176fe9502080f4`.
It passed the separate read-only probe before play, with42.58seconds initialization,
but later exceeded the90-second startup budget in two games. These are different
observations, and a successful smoke check must not hide the later failures.
Host-wide CPU utilization averaged about70% in the failed-start games and60.5%
in the opponent-flag game. Those measurements include other applications and
initialization; they do not establish a specific cause. No heavy teacher or training
job ran alongside these timed games.

**What needs work**

The three losses in which chess was played all ended in the endgame. Their first
verified losing transitions occurred once in the opening and twice in the
middlegame. Treating all three as endgame failures would target the wrong decisions.

* Against v1.41 as White,14.Bd2 was the first losing transition; both teacher
  budgets preferred h3. There were about89seconds left.
* Against v1.41 as Black,12...f5 was the first losing transition with about96seconds
  left. The two teacher budgets preferred different alternatives, ...a6 and ...Qc7;
  there is no stable unique replacement established here.
* Against v1.48 as White,15.Ne5 was the first losing transition; Nb5 was preferred
  at both budgets, with about89seconds left.
* In the drawn Black game against v1.47,56...Rf5 lost a winning advantage that ...h2
  preserved, with18.46seconds left. This is an actual conversion target.
* In the2600 draw,18.h4 was a verified deterioration; the stronger alternatives
  differed by budget. The eventual draw does not erase that earlier mistake.

Across434 candidate decisions, the audit found12 stable errors of at least200cp:
seven in the middlegame and five in the endgame. Some first losing transitions
were smaller than200cp, so the phase counts above and this threshold count describe
different measurements. The two startup losses have zero move examples to train on.

Engineering priority is reliable startup and useful early threat calculation;
several poor moves occurred with ample time. Learning priority is verifying that
corrections to descendant-position values change actual root decisions without
breaking sound choices. Data priority is the new verified alternatives and the
specific missed promotion/conversion, including mistakes in draws and wins.
Use these targeted examples in the bounded [mistake-replay pilot](IMPROVEMENT_CYCLE_16.md).

The candidate's original14-position gate fixed one exposed promotion error, yet
that did not establish general strength. Keep this result as evidence against
promoting on a small puzzle gain alone. All game/source/clock/outcome audits passed;
that statement verifies the recorded startup and flag failures too, not their absence.

For the broader development plan, see [the growth plan](COMPETITION_GROWTH_PLAN.md).
Recent actual competition games are separately documented in
[the current-build sample](COMPETITION_RECENT_GAMES.md); their results are not mixed
with these new local candidate games.
