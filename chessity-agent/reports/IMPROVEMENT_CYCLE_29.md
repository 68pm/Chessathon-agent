# Cycle29: bounded queen-supported king pressure

Cycle28 found weak static king-pressure scores in existing refutations of the
rook error. Two queen/knight attackers could contribute just5cp through the
phase-tapered term before material fell. This is descriptive evidence, not proof
of a cause. Test one new evaluation mechanism on frozen27; keep all other search,
clock, policy, weights, pawn corrections and extension behavior unchanged.

Reuse pressure already counted in classical. For each non-pawn, non-king piece
attacking at least one enemy king-ring square, count one attacker and accumulate
ring hits weighted N/B=2, R=3, Q=5. If that attacking side has a queen anywhere
and at least two such attackers, add min(250, 2*units*units) centipawns for it.
Apply symmetrically after phase tapering. No extra board scan or attack array.
These coefficients, scope and cap are fixed before any measurement; no tuning
after results. Lone-queen activity and queenless attacks receive no new term.

Run eight new correctness cases: independent python-chess attack-set formula
over160 seeded legal random positions; the144 already saved PV positions;
color-mirror symmetry on40 seeded positions; one capped coordinated attack;
queenless and lone-queen zero-term scope (two cases); terminal mate/draw priority
in one combined case; and512-node interrupted-search state/history/accumulator
restoration. Compare evaluation deltas to parent27 using its Python classical
function without compiling another search. Existing parent tests remain archived;
they are not counted as new29 tests. Freeze source and all inputs first.

Keep the full27 tactical rule: selected51 versus29, each17 one-second clock
roots plus3 separate250k-node/8s diagnostics, full history, policy off equally,
cleared search state. Init<=90s, legal/restored/depth>=1, outer time<=1.25/8.25s.
Only strict reduction in repeated clock mistakes plus king avoidingKf1 in at
least one mode and endgame clock avoidingBxe8 permits teacher review. Review all
20 choices/build at80k/320k with compatible frozen cache;<=16M new teacher nodes
before reuse. Require lower clock mean regret at BOTH budgets, no new paired
stable200cp error or mate loss in either mode, king<=50cp both in one mode,
and endgame clock<=50cp both. Additionally require rook regret<200cp at BOTH
budgets in BOTH modes, so baseline timing cannot excuse the motivating blunder.
No exemption for an already losing position. Failed gates are not retried.

Only fullPASS permits strict read-only validation and exactly two120+0.5 games
against51 from unused prepared opening index6, both colors,>=50%score and no
candidate failure before further selection. No automatic release or Elo claim.
Use serial hidden Normal-priority local CPU work,>=2048MiB disk and>=768MiB RAM
before every heavy process,20-minute maximum capacity wait,300-second owned
child-tree bounds, STOP flags. No overlapping JIT/teacher/fit/games.

Engine value correctness is first; runtime/depth effects are measured in the
same fixed probe budget. Learning is second: improving the classical base could
reduce residual correction required, but no fit is justified by these features.
Future fitting needs independently verified opponent continuations and targets
reachable under the existing125cp effective cap. Targeted data are the existing
144 PV positions and17 actual audited roots, with original history/provenance.
Do not relabel descendants with root scores or download broad GM data.
