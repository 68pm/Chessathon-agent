# Cycle 15: queen-aware passed-pawn evaluation pilot

Base: frozen v1.48, preserving its exact faster existence guard. The completed
cycle14 trace shows that Bxe8 g8=Q is evaluated about+364cp despite the teacher's
draw assessment. A passed pawn currently receives the same geometric endgame
bonus whether facing a rook or a queen, without modelling checking resources.

Test one bounded correction: at phase<=8, for a side with no queen facing an
enemy queen, reduce only the passed-pawn endgame multiplier from5 to2. Keep
midgame bonus, material values, all other evaluation and search/weights unchanged.
This is a contextual heuristic, not a universal claim that the queen stops every
pawn. The coefficient and scope are fixed before testing; no adjustment retries.

Check exact scope/delta, colour symmetry, random legal-state preservation and
unaffected material classes against the old evaluator. Then use14 exposed errors:
the previous11 roots plus the3 cycle13 errors. At250k nodes, reuse the unchanged
v1.48 cached11-root measurement and measure only its3 new roots, plus all14 for
the prototype. Require fewer repeated errors, avoid Bxe8 at the motivating root,
and verify newly chosen moves with80k/320k teacher nodes. Require lower mean
capped regret at both budgets and no added verified forced-mate losses before
spending time on a small match pair. Preserve all measurements, including failure.

Engine judgement first; review the demonstrated material-context signal for the
residual network second; existing verified mistakes supply targeted data third.
No new fitting, external download, long consistency study or automatic promotion.

## Completed pilot and package checks

Six scope/symmetry/random-state tests passed. On the 14 exposed positions, repeated
errors fell from 11 to 10. The motivating endgame now selects Rb7 instead of Bxe8;
both teacher budgets agree it preserves the advantage. Mean capped regret fell
from 316.14 to 281.29cp at 80k nodes and 343.93 to 308.00cp at 320k nodes, with no
added verified mate losses. New teacher work was 1.2 million nodes. This improvement
is on exposed development cases, not evidence of a general win-rate increase.

Frozen candidate: `candidates/compiled-queen-pawn-v1`, ZIP SHA-256
`a1cd0bea47752ecec5774ce1d9adeeb05a9147948006e2a1c1176fe9502080f4`.
Read-only validation passed: 42.58s initialization, 232,984,576-byte peak working
set, two legal calls at a 120-second clock, maximum move 3.487s. Filesystem mutation
attempts were blocked; no network or subprocess calls. Elementary tables and the
optional Alien preference were verified. This is an evaluator improvement, not a
newly fitted neural network.

## User-requested short comparison

The user then explicitly requested other versions as well as nominal 2400 and
2600 opponents. Before any new game, declare exactly ten games: one colour pair
each against v1.41, v1.47, v1.48, Stockfish 19 UCI_Elo 2400 and 2600. Use 120+0.5,
at most two simultaneous games, and the same preselected A39 English opening
(source entry 4 from the already prepared starts). Starting lines are replayed
legally before scheduling. No outcomes are used to select or replace the opening.
This controlled but narrow opening sample is a diagnostic, not a broad rating test.

Complete all five opponents even after losses. Finish all timed games before
offline teacher analysis. Independently audit legal moves, clocks, outcomes and
frozen source; then screen own moves and verify suspicious choices at 80k/320k
nodes. Report first warning, first losing transition and missed advantage by phase,
separately from the phase in which each game ends. Preserve every result and PGN.
The selected upload remains v1.41 pending this comparison and practical review.
There is no automatic pool retirement or long consistency requirement.

Completed battery:0W/0D/2L versus41;0W/2D/0L versus47;1W/0D/1L versus48;
0W/0D/2L at2400, both startup failures;1W/1D/0L at2600, with the win caused by
the opponent's clock flag. The candidate is not selected. Read-only preflight
success did not guarantee startup within the later match budget. Preserve the
entire ten-game record and archived v1.49. See
[the complete result and phase diagnosis](COMPETITION_TEN_GAME_REVIEW.md).
