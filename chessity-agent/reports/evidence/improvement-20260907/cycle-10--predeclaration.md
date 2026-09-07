# Cycle 10: conservative null-move search pilot

Base: exact frozen v1.41. Round55's 26.Rc1 is rejected through depth6 because
...Rxe2 appears sound. Offline teacher identifies the quiet 27.Nb6 continuation.
A full-window depth9 child search values Rc1 at +159cp versus Kf1 at +25cp;
the ordinary root cannot finish depth9 within12 seconds. No source corruption
or root-policy fault was demonstrated. Target useful search depth per clock.

Implement a separate conservative null-move prototype. At non-PV nodes only,
depth>=4, not in check, static value>=beta, non-mate window, halfmove clock<60,
and both sides with substantial non-pawn material, test a reduced hypothetical
pass. Never play a pass. Disallow consecutive null moves, suppress pre-pass
repetitions inside the virtual subtree, retain the real halfmove clock, clear
en passant and restore all state. Distinguish its transposition context from
real history. At depth>=7 verify a potential cutoff on the original position
without another null move at that node. No evaluation, policy, data or NN changes.

Run meaningful state/draw/check/mate/budget tests. Then measure all11 exposed
errors (eight earlier confirmation errors and three actual competition errors)
once per build at one second. The cheap gate requires fewer error repeats in
total and no regression in the three real-game roots. Verify changed choices
at80k/320k teacher nodes; require lower mean capped regret at both budgets and
no added verified mate losses. If rejected, preserve evidence and stop this idea.
If it passes, freeze one candidate and check read-only competition operation,
then two colour-paired games against41 before allocating more match time.
No long independent consistency check, rating certification or forced promotion.

Three priorities: engine efficiency first, assess learning after determining
whether deeper search helps, and use existing verified targets before new data.
These roots are development material, not fresh strength evidence. Preserve41.
