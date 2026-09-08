# Cycle 31: bounded root PVS experiment

Predeclared 8 September 2026, before measurements. Selected v1.52 remains unchanged.

## Engine first

Cycle 30 reproduced the wrong preference in all three recent losses at depth 6.
All nine depth-8 branches exhausted their node budgets. More depth is not a
proven cure, but the root currently gives every move a full search window while
the inner search already uses principal variation search (PVS).

Change only root_iteration: after the first root move, scout with a one-point
window around the current best score adjusted for that move's policy bonus.
Any improving scout is searched again at full width. Use the original full
window near mate scores. Preserve all evaluation, weights, search extensions,
move ordering, history, clocks, read-only startup and driver behavior.

One pilot, no timing retries or threshold changes after outcomes:

1. Nine cheap independent tests cover full re-search, fail-hard bounds, positive
   and negative policy bonuses, ties, mate scores, interruption during either
   search, restoration, and AST identity outside the changed root function.
2. One fresh process per build, serial: unchanged v1.52 then prototype. Each
   initializes within 90 seconds, then measures 22 fixed-depth root searches:
   all four recent warnings, the three prior startup king/endgame/rook roots,
   initial position, promotion, real repetition history, and mate in one;
   each with zero and deterministic signed bonuses. Depth 4 except promotion
   depth 3 and mate depth 2. Each attempt has 500,000 nodes and 8 seconds;
   incomplete scores are null and fail the gate. Equal completed root scores
   are required across builds; tied best moves may differ. Each move must be
   legal and leave pieces, state and real history unchanged. Verify mate in one
   ignores bonuses and a 512-node interrupted iteration retains its prior move.
3. Each same worker measures all 21 exposed development roots once at 1 second
   per position, policy disabled equally, fresh TT/history each time. No games.
4. Cheap gate requires all correctness checks, at least 10% fewer aggregate
   fixed-depth nodes, and no decrease in mean completed clock depth.
5. Only if the cheap gate passes, review all 42 clock choices against existing
   root references at 80k and 320k teacher nodes, reusing compatible cached
   analyses. Maximum 16.8 million newly requested nodes. Require no new stable
   paired 200cp error or mate loss, non-increasing mean regret at both budgets,
   and at least one of the four recent warnings improved by at least 100cp
   at BOTH budgets. Keep every observation, including failures.

Passing permits a subsequent read-only check and exactly two predeclared
120s+0.5s games against v1.52, not automatic promotion or an Elo claim. Failing
leaves v1.52 selected and requires a new diagnosis, not an unchanged retry.

## Useful learning second

This is an efficiency experiment, not new neural training. Existing depth-6
rankings and the earlier residual-cap audit show that more epochs are not a
justified intervention. Next learning targets must include verified opponent
counterfactual descendants and fit the actual runtime evaluator's range.

## Targeted data third

Use the 17 retained mistakes and ALL four new v1.52 first warnings, including
the draw's missed advantage and the below-200cp losing transition. Keep the
two competing teacher queen alternatives. No broad game download is needed.

## Bounds and provenance

Freeze sources, candidate manifests, histories, rules and cache seed before
execution. Both 2048MiB disk and 768MiB physical RAM are required before each
heavy process, waiting at most 20 minutes. Respect both STOP flags. A hidden
Windows System PowerShell task starts at Normal priority 4. One CPU-heavy child
at a time; worker tree bound 360 seconds. No new games, fitting, package,
repository permissions, or live competition upload in this pilot.
