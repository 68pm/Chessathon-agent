# Cycle23: at most two check extensions per line

Declared after the completed defensive trace and before this prototype is
measured. At depth8 the selected engine scores37Kf1 at+62cp by expecting...Ne5,
whereas the verified opponent reply...Qc1+ leads to about-750cp. Its traced
deepest endpoint is approximately drawn according to the teacher; simply fitting
that chosen leaf closer to zero would not reveal the missed forcing reply.
The two deepest traced endpoint discrepancies are only48–69cp, much smaller
than the root error. This supports targeting the opponent's forcing sequence
before training only on the engine's chosen continuation.

Engine change: selected51 core plus one extra search ply at a checked node with
depth>=0, spending one of TWO extension credits available per line. The root
passes two credits; recursive children inherit the remaining credits. Once
spent, or after entering negative-depth quiescence, no further extension is
added. Check evasions, ordinary quiescence, draw/terminal rules and global
node/clock/ply caps remain. Extension capacity affects a node's future search,
so salt the transposition context with the remaining credit count. Keep actual
repetition history separate and unchanged. No quiet-check or aspiration code
from rejected prototypes, evaluation, policy, model, table or clock changes.

Learning need: hold weights fixed. The completed trace shows the importance
of opponent counterfactual replies, not only the student's current PV endpoints.
Future value targets should include the verified refutation and respect the
125cp correction capacity; no fit is justified by this engine experiment alone.
Data need: retain the same17 audited roots and the three new fixed-node
diagnostics, plus the existing forcing-line references. No broad download.

## Fixed gate

Ten focused cases check exact score/node parity with the selected core when
credits are zero, inherited credit limits, transposition separation between
credit counts, mate/draw precedence, interruption restoration and real repetition.
Compilation happens before correctness search deadlines. Candidate state is
frozen before tests; all failures are preserved and concrete test/code issues
must be diagnosed without changing performance acceptance criteria.

Use the same bounded measurement structure as21 with this new engine: baseline51
then prototype23,17 one-second clock roots each and the three new roots at250k
nodes/8-second safety cap, policy disabled equally and full history restored.
Initialization<=90s, clock probe outer time<=1.25s, node probe<=8.25s,300s owned
process-tree timeout. Capacity>=2048MiB disk and>=768MiB free RAM before each
heavy process, max20minute guard wait, serial work, respect STOP flags.

Require strictly fewer repeated errors on17 CLOCK roots and avoid37Kf1 in at
least one king-root probe. Only on cheap pass, verify all20 choices/build at
80k/320k with cached references (<=16Mnew nodes before cache). Require strictly
lower mean regret on17clockroots at BOTH budgets, no newly stable paired200cp
error or mate loss in either mode, and one king choice within50cp at both
budgets. Report the fixed-node cases separately and keep every result.

Pass permits strict read-only packaging and exactly two120+0.5 games versus51
from the next unused opening index6, both colours; require>=50% score and no
candidate operational failures before considering a small follow-up. No
automatic promotion, Elo claim, changed thresholds or long consistency study.
