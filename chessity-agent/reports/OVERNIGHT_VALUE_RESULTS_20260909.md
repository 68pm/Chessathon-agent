# Rule-aware value learning: first bounded fit

The new original network is experimental and was not selected for upload.
The static gate required at least2% lower broad validation MAE and10% lower
independently labelled descendant validation MAE. It passed only the first part.

| Evaluation | Frozen53 classical | New value correction | Improvement |
|---|---:|---:|---:|
| 2,000 broad held-out positions | 230.750cp | 210.791cp | 8.65% |
| 31 held-out descendant positions | 223.145cp | 211.980cp | 5.00% |

This is evaluation error, not game performance or Elo. No new full games were
allocated to this failed static gate. v1.53 remains retained unchanged.

The fit used20,000 broad training positions plus101 eligible independently
labelled training descendants. The143 candidate descendants received their own
80k/320k Stockfish analysis;11 failed eligibility, leaving101train/31validation.
They came from eight historical reviewed games grouped before labelling, including
all four E55 local games in one group. Parent action rewards were provenance only.
Broad CP perspective was verified against training/dataset.py's board.turn.

Architecture:781inputs/64clipped-ReLU units/original random weights, including
four relative castling flags, eight legal en-passant file flags, and draw clock.
Twenty fixed epochs,1,580Adam updates, .75broad/.25game-balanced target gradients.
No validation-based epoch or seed selection. Broad validation alone selected
blend1 from0/.25/.5/1, then the descendant holdout was evaluated once.
The residual is bounded to600cp. It has not been integrated into search runtime.

Three tests passed: finite-difference Huber derivatives, colour/mirror/rule state
including pinned illegal en-passant, and 0x88 perspective conversion. Ruffpassed.
Training source: training/rule_value.py; run:runs/overnight-20260909/rule-value-01.
ModelSHA256:90bf01a13aa71751727f970f754410b1e40a68b021665ba49949a8cdd2683b9a.

Broad annotations have uncontrolled historical teacher/depth settings. Exact and
mirror filtering and ECO/source grouping reduce leakage without proving semantic
independence. Do not tune another fit against these same descendant holdout scores.
