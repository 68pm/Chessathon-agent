# Cycle 32: diagnose two recent tactical losses at descendant positions

Predeclared 8 September 2026 before measurements. No engine or model changes.

Cycle 30 retained wrong depth-6 rankings, and cycle 31's root PVS saved fixed-depth
work without changing any clock-limited move. Before another search or evaluation
patch, identify what the engine expects after `30...Bxf2+` and `26.gxf6 e.p.`.

## Engine first

Use the unchanged selected v1.52 and the two corresponding recent-game histories.
For each played move and every distinct verified alternative, capture the
principal variation from exact transposition-table entries after one full-window
depth-6 forced-branch search. This is five branches: Bxf2+/Qf5/Qd3 and gxf6/Rdd3.
Honor the remaining check-extension credits in table context, search depth and
trace traversal. Stop explicitly at missing/nonexact entries or quiescence;
never invent a continuation or present an incomplete trace as a full PV.

Each branch has the same 500,000-node/8-second bound as cycle 30. This revisits
the branches to capture previously unrecorded internal continuations, not to
retry a strength gate, change their rankings or increase the budget. Assert
completed scores match cycle 30's same depth-6 records. Keep failures.

Also restore the existing teacher best/played principal variations at prefixes
4 and 8 from BOTH verification budgets. Retain both queen alternatives and both
rook replies after the en passant fork. Deduplicate identical complete histories.
Together with five student trace endpoints there are at most 21 endpoints.
At each, record selected classical evaluation, raw material, coordinated king
pressure and passed-pawn exposure features. Run a bounded local quiescence
probe, at most 100,000 nodes/2 seconds per endpoint. Preserve board, accumulator,
history and legal/terminal state; incomplete scores are null.

One production student process, initialization at most 90 seconds. Maximum
student work 4.6 million nodes; owned process-tree wall bound 360 seconds.

## Useful learning second

After the student exits, independently analyze each nonterminal endpoint at
80k and 320k Stockfish nodes, from its complete history and side-to-move.
Maximum 8.4 million requested teacher nodes. Record finite and mate scores
separately, root-perspective conversion, and student-minus-teacher differences.
Root scores are not descendant labels. These are diagnostic references, not
automatically accepted fitting labels. Check whether errors exceed the earlier
125cp effective correction range before proposing a compatible learning change.

This distinguishes optimistic leaves from missed opponent continuations. It
does not establish that a particular static feature caused the game loss.

## Targeted data third

Only two already audited high-regret recent mistakes and their verified
counterfactual lines are needed. No broad game download, new match, repeated
training epoch or package. The remaining recent warnings and 17 retained roots
remain regression coverage for a later justified code change.

## Execution and decision

Freeze inputs, source, selected file manifest and rules. Serial local CPU work;
both 2048MiB free disk and 768MiB physical RAM before every heavy process, with
capacity waits bounded at 20 minutes. Honor both STOP flags. Hidden Windows
System PowerShell task, Normal priority 4 from launch. Teacher work begins only
after the student exits and receives its own capacity check before Stockfish.

Save every trace, stop reason, leaf and teacher result. Critique the mechanism
before choosing the next single implementation hypothesis. No promotion,
consistency study, Elo claim or automatic fit is authorized by this diagnosis.
