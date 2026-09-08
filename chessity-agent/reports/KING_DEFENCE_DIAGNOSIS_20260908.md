# King-defence diagnosis: the missed opponent reply

**Selected upload remains v1.51.** A bounded trace explains the remaining37Kf1
mistake more specifically. The selected search predicts...Ne5 at depth8, whereas
the existing independently verified refutation starts...Qc1+. No model or playing
code changed during this diagnosis.

| Forced white move | Depth4 | Depth6 | Depth8 |
|---|---:|---:|---:|
| Kf1 | +113cp | +69cp | +62cp |
| Kg2 | +62cp | +62cp | +48cp |

All six full-window searches completed within their750k-node/15-second limits,
with exact, legal, history-matching table traces reaching the requested main
depth. Initialization was72.519seconds. In the bad Kf1 branch the deepest trace
continued...Ne5 Re2 Qf3+ Ke1 Nxd3+ cxd3 Qxd3. The teacher considers that endpoint
approximately drawn; it is not the opponent's strongest continuation.

The earlier verified Kf1 refutation begins...Qc1+ Kg2 Ne1+ Kh3 Qh6+ Kg4 Qe3,
and scores-747/-761cp at80k/320k. The student's depth8 branch value of+62cp
therefore depends on missing that stronger opponent choice. More depth alone
and the rejected single quiet-check layer had not corrected it.

Six traced endpoints received separate teacher analysis after the student exited,
using2.4million new nodes. The two deepest quiescent values were+62/+48cp;
teacher estimates were-7/0cp and-12/0cp, differences of48–69cp. Fitting only those
selected leaf values would not reveal the missing opponent line. Other endpoints
had larger discrepancies, including one underestimation; they remain diagnostic
data, not automatically accepted training labels or proof of a whole-game repair.

## Bounded follow-up

The [cycle23 plan](IMPROVEMENT_CYCLE_23.md) tests at most two check extensions
per line using the selected51 engine. Each qualifying checked node spends one
credit to preserve a search ply. Remaining credits are included in transposition
context so values from different future search budgets are not reused blindly.
No rejected aspiration/quiet-check mechanism or changed weights are bundled.

Engine work targets the forcing opponent sequence. Future learning needs such
counterfactual opponent replies as well as the student's own chosen endpoints,
with objectives compatible with the125cp residual limit. Existing actual-game
history and teacher references supply the targeted data. No broad download,
training, ordinary matches, new release or Elo claim comes from this diagnosis.

[Exact student traces](evidence/king-defence-diagnosis-20260908/cycle-22/student.json) ·
[Leaf teacher analysis](evidence/king-defence-diagnosis-20260908/cycle-22/teacher.json) ·
[Evidence manifest](evidence/king-defence-diagnosis-20260908/manifest.json) ·
[Current selected agent](IMPROVEMENT_RESULTS.md)
