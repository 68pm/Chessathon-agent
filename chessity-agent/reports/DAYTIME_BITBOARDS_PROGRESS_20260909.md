# Pawn-bitboards candidate: first six completed games

This is a development snapshot from `pawn-bitboards-progress-01`, before the
2600 pair finishes. The candidate won both colours against v1.54 and v1.53, then
lost both colours against the nominal 2400 setting. All games used 120s + 0.5s
and frozen playing weights. These six games do not establish calibrated Elo.

All 277 candidate moves were reviewed: 152 positive labels and 12 corrections.
The existing phase classifier places eight corrections in middlegames and four
in endgames; none of the flagged corrections were classified as opening moves.
An absence of a correction label is not proof that a move was objectively best.

The clearest new problems are defensive decisions:

- Against 2400, Black13 ...f6 weakened the king's position. Independent teacher
  budgets valued the best defence at -79/-39 cp and the played move at
  -459/-527 cp. They disagreed on the best alternative, so no stable policy
  target was assigned. The bishop check on h7 and queen move to g6 are central
  to the threat. At move15 the engine took a knight with ...gxf3; both budgets
  preferred ...f5. At move17 it took more material with ...fxg2 while both
  budgets preferred the defensive exchange sacrifice ...Rf7.
- In the White loss, 35.Qd3 allowed ...Rxc3. The teacher preferred 35.Bc4 at
  both budgets. The position was already worse, but the error enlarged the
  disadvantage from -114/-204 cp to -420/-439 cp.
- In a win over v1.54, White23 Qe3 surrendered a large advantage to a knight
  check on f3; Bg3 preserved the advantage. Winning the game does not erase
  that tactical error. Black also missed a teacher-supported mate at move22
  in the other win, choosing Qe2 instead of Rxf2.
- Against v1.53, Black repeatedly moved rooks while the teacher preferred the
  pawn break ...a4 at moves30,33 and35. This is a specific endgame activity
  target, despite the eventual win.

The unrun descendant diagnosis now includes the independently supported new
White35 and Black15 alternatives alongside four existing loss/field roots. It
will record actual bounded student continuations and label each eligible leaf
independently. Root scores are not leaf targets. The current network's domain
excludes low-phase endgames, so these rook/pawn examples require separate search
or endgame work; fitting that network alone would not address them.

The new candidate has passed the two archived-opponent score gates. Retain the
current release until the full declared screen and review finish. The 2400
result is weaker than v1.54's earlier 0W/1D/1L in a different short screen;
do not hide that evidence or claim improved rated-opponent performance from
the four archived-opponent wins.
