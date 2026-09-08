# Losses, draw and learning results — 8 September 2026

**Chessity v1.53 remains the recommended upload.** Three implemented experiments
failed to improve decisions in the selected positions. The fitted network also
lost all four requested rematch games. No new release has replaced v1.53.

## Completed rematch

The experimental network played one game as each colour against Stockfish's
nominal 2400 and 2600 settings, at **120 seconds + 0.5 seconds per move**. These
were the same E55 opening positions used in the earlier v1.53 comparison. This
small, previously analysed sample does not establish a calibrated Elo rating.

<!-- REMATCH_RESULT_START -->

| Nominal opponent | Trained candidate wins | Draws | Losses | Operational failures |
|---|---:|---:|---:|---:|
|2400|0|0|2|0|
|2600|0|0|2|0|

Highest checkmate win by this experimental model in this rematch: **none**.
Conditional 2800 outcome: `skipped_no_played_2600_win`.

The recommended upload is still **v1.53**. Its earlier results from the same
opening remain **2400: 1 win, 0 draws, 1 loss; 2600: 0 wins, 1 draw, 1 loss**.
The experimental results belong to a separate model. No v1.54 release or
replacement of the best ZIP was made.

Strict read-only checks passed with 75.03s startup, two legal calls,
a maximum move time of 3.486s and peak memory of 223.3 MiB.
The original 90s combined watchdog failed without stage telemetry. The staged
validator separated 90s initialization from 30s post-ready checks; all actual
checks passed. Its final report writer then created a circular reference.
Complete saved telemetry was verified and recovered without replaying the
engine checks. All failures, corrected sources and original timing limits
are preserved. The final games ran only after this verified package result.

<!-- REMATCH_RESULT_END -->

## What the original games revealed

The original exact v1.53 games scored a win and a loss against 2400, and a draw
and a loss against 2600. Both losses were checkmates; the draw was threefold
repetition. All four ran without operational failures.

All 236 of our moves were screened. Suspected errors received independent
Stockfish analysis at 80,000 and 320,000 nodes. Nine finite-score mistakes lost
at least 200 centipawns at both budgets; 25 mate-scored positions were retained
separately. The 2400 win also contained three large missed opportunities.

| Original game | Critical decision | Finding |
|---|---|---|
| Black loss vs 2400 | **20...Qxc6** | **20...bxc6** was more resilient. At 80k / 320k / 1.28M nodes, best values were −143 / −120 / −80 cp versus −515 / −542 / −518 cp for the queen recapture, from Black's perspective. **21.Rxe4** and the bishop–queen attack undermine the recapture. |
| Black loss vs 2600 | **14...Qh4**, then **15...Nac3** | The queen sortie worsened the position. **15...Nb6** was more resilient: −230 / −277 cp versus −600 / −602 cp after ...Nac3. King safety and knight coordination mattered more than these attacking moves. |
| White draw vs 2600 | **35.Bc1**, then **79.Rxd7** | **35.c5** preserved +282 / +337 cp versus −4 / +6 cp after Bc1. At move 79, **Rf7** or **c8=Q** held roughly equality while Rxd7 fell to −437 / −431 cp. The later repetition saved a losing position. |
| White win vs 2400 | **20.Bxf6**, **24.g4**, **30.h5** | Stronger continuations included **Nf3**, **Ra7** and **Kf2**. Conversion and king activity still needed work despite the checkmate win. |

The initial 20k-node screen missed 20...Qxc6. A 379 cp fall between adjacent own
turns triggered the deeper review. **19...Rad8 was not a verified major error**;
21...fxe4 worsened an already bad position.

The sample shows some ability to create dangerous advanced pawns, find forcing
attacks and retain defensive chances. Weaknesses include anticipating opponent
replies, valuing piece-versus-pawn endings and preserving advantages. Both losses
were Black in one opening; this does not establish a general colour weakness.
Disabling draws would not repair the earlier mistakes.

## Engine changes tested

All three candidates were compared on the same 17 exposed positions, with one
second per position. Different completed depths and runtime variation limit
what this small screen establishes. Mean regret is evaluation lost compared
with the teacher's best move; lower is better.

| Candidate | Errors of at least 200 cp at both budgets | Mean regret, 80k / 320k | Decision |
|---|---:|---:|---|
| Unchanged v1.53 | 5 | 122.06 / 139.82 cp | Retain |
| Extra full ply for bishop–queen battery threats | 7 | 154.18 / 180.12 cp | Reject |
| Bonus for supported passed pawns in queenless positions | 12 | 262.71 / 287.24 cp | Reject |
| Learned local position-value network | 9 | 209.12 / 236.29 cp | Reject |

The two engine changes each passed four correctness tests. Correct implementation
did not translate into stronger play. Two initial battery-test harness import
failures preceded compilation or probes; the corrected worker completed all 17
positions. Failed attempts and original thresholds are preserved.

## What was actually trained

Four critical roots generated nine explicit depth-six alternatives, all completed
within 500,000-node / eight-second limits. The original engine still preferred
the mistakes:

| Alternatives | Engine score for mistake | Engine score for better alternative |
|---|---:|---:|
| 20...Qxc6 / ...bxc6 | −64 cp | −191 cp |
| 15...Nac3 / ...Nb6 | −119 cp | −160 cp |
| 35.Bc1 / c5 | +314 cp | +178 cp |
| 79.Rxd7 / Rf7 / c8=Q | +87 cp | −29 / −31 cp |

This supports a problem in valuation or searched continuations beyond simply
needing more nodes. Actual histories and alternatives produced 34 descendant
positions. Each received independent 80k / 320k labels; no root evaluation was
copied onto a later position.

A continuation after 35.Bc1 reached two bishops against a rook. The student
evaluated it at +351 cp; the teacher gave −14 / −7 cp. A descendant of 79.Rxd7
with king and advanced pawns against a rook received +94 cp from the student
but −457 / −434 cp from the teacher.

Filtering excluded transient recaptures, checks, mate scores, unstable labels
and relevant history that could not be represented. **22 eligible new positions
plus 15 earlier independently labelled positions** yielded 37 training examples.

The 768-input / 32-unit clipped-ReLU architecture was fitted using local
piece-pattern features and one ridge-regression output fit. Training mean
absolute error fell from **309.5 to 156.87 cp**. This is supervised fitting on
those examples, not improved Elo or evidence of generalisation.

The correction applies only near represented piece patterns. Runtime guards
disable it for castling/en-passant rights, high half-move clocks and repetition
contexts that the input cannot encode. Raw targets were not clipped; runtime
corrections were capped at 1500 cp. Five correctness tests passed. All 17
practical probes were legal, restored state and finished on time.

The weaker position tests and four rematch losses mean this model stays an
**experimental checkpoint**. Repeating this fit without a new hypothesis is not
justified. The next useful work is better evaluation of piece-versus-pawn
endings and coverage of defensive alternatives, followed by a small test of
actual move quality before replacing the upload.

## Reproducibility notes

Evidence includes raw and annotated PGNs, both teacher budgets, failed trials,
fitted weights, source snapshots and hashes. No long consistency study ran.

One supplemental explanation string incorrectly calls a root 14...Na4; its
saved move, FEN and analysis refer to **14...Qh4**. Earlier diagnostic labels
also abbreviate **79.Rxd7** as Rd7. The PGN verifies the capture, and this report
uses the correct notation. Frozen source and data remain preserved.
