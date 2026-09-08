# Cycle22: explain the Kf1/Kg2 evaluation discrepancy

Cycle21's quiet-check prototype passed ten corrected correctness cases but
failed its position gate:14/17 versus15/17 original clock-budget errors, with
Kf1 unchanged in both probe modes. Its extra checking layer did not earn a
package or match. Preserve that result and v1.51; do not widen the layer or
retry either rejected mechanism without a new diagnosis.

Engine need: determine what the selected engine actually sees after37Kf1 and
37Kg2, instead of proposing another search change from depth alone. Learning
need: identify whether its quiescent endpoint values disagree with independently
verified leaf values, and whether the allowed125cp residual contribution could
address any observed discrepancy. Data need: use the existing exact game history,
both verified branch references, and at most six resulting leaf positions.

Use only the selected51 engine. Reconstruct startup19-game-001-ply-062 from the
frozen17-root data. Force each of g1f1 and g1g2 at total depths4,6,8, in that
declared order by depth then move. Clear search state between cases. Each forced
branch gets750k nodes and15seconds; interrupted results have no usable exact
score. Record full-window score, runtime and node usage with root policy disabled.
Initialization is recorded separately and must finish within90seconds.

For completed cases, follow only matching, exact transposition entries through
at most the remaining main-search depth. Validate legality, position key, history
context and halfmove counter; stop explicitly on missing/overwritten/bounded
entries. A partial trace is not a complete principal variation. Record its endpoint
and static value. On each unique nonterminal endpoint, evaluate the selected
quiescence search once with250k nodes/3seconds, retaining incomplete flags.
No candidate code, model weight, time policy or dataset is changed.

After the student process exits, independently analyse each unique endpoint at
80k and320k nodes (at most2.4million new teacher nodes), reusing duplicate leaves.
Preserve complete board histories; terminal positions need no teacher search.
Report root-perspective scores and the125cp correction capacity as context,
not proof that a new network or search change will fix a whole game. Teacher
estimates remain finite. No fit, root replay-until-correct, ordinary match, new
release or Elo conclusion is authorized by this diagnosis.

Require disk>=2048MiB and free physical RAM>=768MiB before each heavy process,
bounded20minute wait, serial student then teacher. Student process hard timeout
300seconds, teacher180seconds, with owned Windows process-tree cleanup on timeout.
Respect STOP flags. Keep original source and all earlier tests/gates immutable.
