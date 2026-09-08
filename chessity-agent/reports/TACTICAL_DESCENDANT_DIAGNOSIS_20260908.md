# Tactical descendants: missing defenses and inaccurate position values

**Two different weaknesses remain. v1.52 is unchanged.** The bishop-sacrifice
line relies on an opponent continuation that actually favors Chessity, while
the en passant line reaches a position Chessity substantially overvalues.
This diagnosis supports different next interventions for the two errors.
No new games, training updates, package or Elo claim resulted.

Cycle 32 completed on 8 September at 13:59 BST. One unchanged production v1.52
process captured five forced depth-6 branches with the same bounds as cycle 30,
adding previously unsaved internal continuations. All five completed scores
matched cycle 30 exactly. Four table traces reached quiescence; the Qd3 trace
stopped at a missing or nonexact table entry and is explicitly partial.

Seventeen unique endpoints came from those traces and prefixes 4/8 of both
budgets' existing best/played teacher lines. Each retained its actual history.
Independent 80k/320k analysis was performed on the endpoints themselves;
root scores were not reused as endpoint labels.

All scores below are centipawns from the original Chessity side's perspective.

| Root choice | Student branch score | Endpoint quiescence | Endpoint teacher, 80k / 320k | Trace |
|---|---:|---:|---:|---|
| Black Bxf2+ | +378 | +378 | +671 / +690 | Reached quiescence |
| Black Qf5 | +57 | +57 | -12 / -11 | Reached quiescence |
| Black Qd3 | +57 | +173 | -24 / -11 | Partial: missing/nonexact entry |
| White gxf6 e.p. | +137 | +137 | -298 / -339 | Reached quiescence |
| White Rdd3 | +100 | +100 | +220 / +200 | Reached quiescence |

## Bishop sacrifice: the student's imagined line is favorable to Black

The exact table continuation was:

`...Bxf2+ Rxf2 ...Qe1+ Rf1 ...Qe3+ Kh1 ...dxc5 Qe7`

The resulting position is favorable to Black according to the independent
teacher, even more than the student's +378 estimate. Simply fitting this
student-chosen endpoint toward its teacher score would increase its apparent
attractiveness. It would not teach the opponent's stronger defense.

In the existing verified refutation, Black instead reaches the sequence
`...Qxf1+ Kxf1 ...Rxc5 Bd5` after the initial checks. At that descendant,
Chessity's quiescence score is -18 but the teacher gives -487/-531. The earlier
prefix after `...Qe1+ Rf1` also differs strongly: +97 versus -528/-550.

These observations support investigating the opponent's defenses after the
student's `...Qe3+`, as well as the value of the forced-exchange descendants.
They do not identify the correct reply to Qe3+ by themselves, or prove which
single feature caused the original error.

## En passant: the reached position itself is overvalued

The student expects:

`gxf6 ...Bh5 Rdd3 ...Bxf3 Rxf3 ...h5`

It values this endpoint at +137; the teacher gives -298/-339, an error of
435/476cp. Quiescence finishes immediately, so captures alone do not expose
the remaining positional problem there. The f6 passed pawn contributes a
50cp middlegame / 125cp endgame bonus before tapering, but its bonus alone
does not account for the discrepancy.

The verified alternative refutation eventually includes `...Kxf6`. Even after
that pawn disappears, another descendant is scored -101 by Chessity versus
-480/-493 by the teacher. Removing only this passed-pawn bonus therefore cannot
explain every observed value error. Exchange balance, king activity, pawn
vulnerability and rook activity need a measured evaluation review rather than
a rule tied to the en passant move or these exact squares.

## Learning implications and next work

Thirteen of the 17 endpoint errors exceed 125cp at both budgets; eleven exceed
200cp. One endpoint is in check, and all teacher scores here are finite. These
are diagnostic examples, not automatically accepted fitting data. The earlier
effective 125cp residual correction range cannot represent many of the measured
errors. More unchanged epochs are not a solution.

The next bounded intervention should locate the missing defensive continuation
after Qe3+, and use the counterfactual exchange/rook-ending positions when
assessing a general evaluation change or a compatible learned value objective.
Keep both queen alternatives, the incomplete Qd3 trace, and the other 19
development roots. No broad GM-game download is currently needed.

## Execution and evidence

Initialization was 49.919 seconds. Student work totaled 375,155 nodes, including
all five main searches and 17 completed quiescence probes. The longest branch
took 0.701 seconds. All piece/state/accumulator/history and source checks passed.
The independent teacher requested 6.8 million nodes after the student exited.
No branch or quiescence probe exhausted its limit.

The hidden Normal-priority task exited successfully and was removed after
confirming no owned chess process remained. Sources and the selected upload
are unchanged. See [predeclared bounds](IMPROVEMENT_CYCLE_32.md) and the complete
[evidence manifest](evidence/tactical-descendants-20260908/manifest.json).
