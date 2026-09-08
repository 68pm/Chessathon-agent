# Search development, 8 September

Selected upload remains **v1.51**, the startup revision of v1.41. The latest
aspiration experiment did not pass its declared position gate. No new numbered
release, training, ordinary match or Elo result followed from that experiment.

## Completed cycle20

Both builds used the recovered startup. All17 exposed mistake positions were
measured twice at one second, with fresh processes in the declared order and
root policy disabled equally. Source manifests, history and legal-move checks
passed. Initialization ranged50.751–84.986seconds. Maximum observed outer
position time was1.0408seconds, below the1.25-second diagnostic ceiling.

| Build | Mean completed depth | Original mistakes repeated, out of34 probes |
|---|---:|---:|
| Selected51 baseline | 5.529 | 28 |
| Aspiration prototype20 | 5.735 | 29 |

The0.206-ply gain missed the0.25 requirement and repeated errors increased.
The cheap gate failed, so no new teacher nodes, training or match games were
spent on it. This sample deliberately consists of known mistakes and is not
an estimate of the agent's overall blunder rate. The original cycle17 ENOSPC
failure and all four new passes remain preserved; no timing retries are planned.

Both builds continued to choose the losing37Kf1 line at depth7, with the same
75cp evaluation; prototype20's extra depth did not repair the defensive move.
Both also retained16...f4 at depth6. The Rc8 error appeared in both prototype
passes and one baseline pass. No one pass was selected to hide the other.

## Next bounded hypothesis: cycle21

The current quiet-leaf search examines captures/promotions and answers checks,
but does not initiate non-capturing checks at a quiet leaf. Prototype21 adds
only one initial quiet-check layer, retaining all check evasions and existing
draw/terminal rules. It uses the selected51 engine and startup, with no rejected
aspiration, changed evaluation or new weights mixed in. This is a hypothesis
about threat recognition, not a proved explanation or repair of the entire loss.

The [predeclared cycle21](IMPROVEMENT_CYCLE_21.md) requires ten tactical/restoration
checks, then two bounded processes: all17 roots at one second and the three
new roots at250k nodes with an8-second safety cap. Only a useful king-defence
change and fewer clock-budget error repeats permit a bounded teacher review.
No ordinary games or new download are authorized by a position result alone.

Engine code remains first. Learning stays fixed for this isolated search test;
the previously diagnosed125cp capacity mismatch still needs a compatible
training objective before another fit. Targeted data consists of the existing
verified errors and complete histories, without new broad downloads. The long
independent consistency study remains abandoned.

[Cycle20 predeclaration](IMPROVEMENT_CYCLE_20.md) ·
[All saved evidence](evidence/search-cycle20-20260908/manifest.json) ·
[Gate result](evidence/search-cycle20-20260908/cycle-20/gate.json) ·
[Selected agent and actual games](IMPROVEMENT_RESULTS.md)

The first cycle21 attempt stopped at test collection because its utility import
pointed to the older root engine package. No test body, compilation, position
probe or training ran. The original failure is preserved; a separate corrected
test entry point uses an AST-identical existing arrays utility. Candidate code,
cases, thresholds and targets are unchanged. See the
[collection recovery note](QUIET_CHECK_COLLECTION_RECOVERY.md) and
[original failure evidence](evidence/quiet-check-collection-failure-20260908/manifest.json).
