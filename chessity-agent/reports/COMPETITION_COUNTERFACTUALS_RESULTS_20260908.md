# Defensive alternatives and rook-ending descendants

The bounded review of the five requested positions is complete. It used exact
v1.53, actual game histories and independent labels on the resulting positions.
There is **no new neural fit, released version or Elo claim** from this review.

## Concrete findings

- **The rook ending is undervalued.** After Rf1/Re1, the student accepts ...Nxa4
  but then shuffles its rook instead of activating its king. The two traced
  endpoints have static and quiescence values of **−19cp**, while independent
  analysis gives **+190/+203cp**. The original root therefore prefers Ra1's
  immediate threefold score of zero. This is an evaluation/planning problem,
  not a failure to detect the actual repetition.
- **Kg4 is part of the useful plan.** A teacher continuation is Re1 Nxa4 Kg4
  Kf7 Rd1 Nc5 Rxd6 a4. The king approaches the kingside pawns while the rook
  works on d6. Independent values along these descendants retain an advantage;
  the advantage is not a proven forced win. The previous small king-distance
  bonus failed and is not being increased blindly.
- **The safe Bxe3 exchange is undervalued.** After Bxe3 Rxe3+ Kh2 a6, the
  student gives −250cp against the teacher's −11/0cp. The h6 alternative is
  similar: −245cp versus −7/−2cp. Removing the attacking bishop leaves a much
  more defensible position than the engine estimates.
- **Some dangerous alternatives are overvalued.** The Ne2 continuation in
  round 62 has quiet descendants valued at +492cp versus −368/−385cp, and
  +481cp versus −377/−447cp. These are substantial valuation errors even after
  local forcing captures have been searched.
- **Mating threats remain a search problem.** Rxb7 permits ...Qe3+ followed
  by mating attacks. Several independently labelled descendants are mate
  scores; these stay tactical regression cases, not ordinary centipawn labels.

## Bounded search results

Each of eleven forced choices received one depth 6 attempt capped at 500k nodes
and 8 seconds. Seven defensive branches reached the node cap and retain null
scores. Four completed: Qe4's trace is partial, Ra1 reaches the actual repetition,
and the Rf1/Re1 traces reach quiescence. No incomplete score is treated as exact.

| Round / move | Forced choice | Student root score, cp | Trace status |
|---|---|---:|---|
| 61 / 26 | Qe3 | Unavailable: node cap | No completed trace |
| 61 / 26 | f3 | Unavailable: node cap | No completed trace |
| 62 / 27 | Ne2 | Unavailable: node cap | No completed trace |
| 62 / 27 | Qe5 | Unavailable: node cap | No completed trace |
| 66 / 28 | Ba3 | Unavailable: node cap | No completed trace |
| 66 / 28 | Bxe3 | Unavailable: node cap | No completed trace |
| 66 / 32 | Rxb7 | Unavailable: node cap | No completed trace |
| 66 / 32 | Qe4 | -100 | missing_or_nonexact_transposition_entry |
| 68 / 80 | Ra1 | 0 | terminal |
| 68 / 80 | Rf1 | -19 | quiescence_reached |
| 68 / 80 | Re1 | -19 | quiescence_reached |

Initialization took 45.802s. There were 47 measured calls and 4,092,458 student
nodes, with no new compiled signatures, state/history corruption or wall-bound
failure. Of 36 nonterminal endpoint quiescence probes, 35 completed; the remaining
probe reached its 100k-node cap and stays null. All 37 history-distinct endpoints
are preserved, including the terminal repetition. Stockfish independently
reviewed 36 nonterminal endpoints at 80k/320k, requesting 14.4M nodes within 24M.

## Learning targets and safeguards

The first export identified 21 potentially usable scalar targets. Inspection
showed that some still contained unresolved captures: for example, a temporary
queen loss followed by an available recapture produces a huge static-versus-
teacher gap that should not simply be fitted into the static evaluator.
The first export and source are preserved; a second, explicitly stricter export
keeps **15 distinct quiet targets**, excluding 22 records from direct fitting.

The exclusions cover mate/unstable labels, checks, incomplete quiescence,
unresolved tactical swings, repetition/draw-clock context, hidden castling/EP
rights and duplicate piece inputs. All records remain available for auditing and
search tests. Five focused tests pass, checking perspective, repetition,
unclipped target values, duplicate weights and pending recaptures.

**14 of 15 eligible corrections exceed the earlier effective 125cp residual
range; three exceed 500cp.** The present runtime's neural leaf correction is
disabled. The exports therefore retain raw, side-to-move values and do not
silently clip or apply an incompatible fit. Useful training needs a representable
position-value objective, whole-game separation and a matched control before
promotion. All these examples are exposed development data, not held-out proof.

Files: `learning-targets-v2/independent-descendants.jsonl` contains the current
export; `defensive-rook-continuations.pgn` contains five games with the legal
student/teacher alternatives and original histories. Original PGNs and labels
remain unchanged. No root label was copied onto an unrelated descendant.

## Requested match screen

The current selected v1.53 will play one 120s + 0.5s colour pair at nominal 2400 and
one at 2600. A checkmate win against 2600 triggers a further pair at 2800. The E55
opening was selected before these diagnostic results. New neural weights have
not been fitted; the match results must be attributed to exact v1.53. No long
consistency study, autonomous overnight restart or live competition upload.
