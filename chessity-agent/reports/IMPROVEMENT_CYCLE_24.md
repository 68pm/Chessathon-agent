# Cycle24: diagnose the check-extension rook regression

Cycle23 repaired Kf1 to Kg2 and reduced mean error, but failed the declared
no-new-error rule. At the already losing rook root, the clock choice changed
from Rd3 (64/68cp regret) to Rc8 (283/284cp). With 250k nodes, the prototype
instead chose Nd5 (138/117cp). The baseline itself changes from Rd3 at its
clock horizon to Rc8 at its deeper node horizon. Do not weaken the original
rule or repeat its timing measurements to select a favourable outcome.

Before another engine change, compare full-window values of Rc8, Rd3, Nd1 and
Nd5 at depths5,6,7 for selected51 and the frozen two-credit prototype. This
isolates forced-branch horizon effects from root move ordering and iterative
search history. Clear transposition/ordering state for each branch and restore
the exact game history. Different extension budgets mean nominal depths do
not imply equal work; report both nodes and completed depth.

Exactly two serial student processes, twelve branches each, maximum500k nodes
and8seconds per branch. Initialization must finish within90seconds. Record an
interrupted branch as incomplete with no score, not as a zero evaluation.
Verify legal root moves and restored board/history/accumulator after every call.
Require2048MiB free disk and768MiB free physical RAM before each heavy process,
wait at most20minutes, use hidden Normal-priority execution and respect STOP flags.
Each student subprocess also has a300second outer timeout that terminates only
its owned process tree, including the Windows venv launcher child.
No additional teacher calls, training, ordinary games or package changes.

Engine work: determine whether the remaining loss is a horizon-dependent value
ordering or an ordering/principal-variation-search discrepancy before choosing
an implementation. Learning work: retain the conclusion that teacher opponent
replies, rather than only student-selected leaves, may supply useful targets;
do not fit this exposed example alone or blindly raise the125cp residual limit.
Data work: reuse this exact audited game history and both existing teacher
budgets. No broad data collection is needed.

This is a diagnostic, not a promotion test. Preserve incomplete branches and
all prior failures. Selected51 remains unchanged. Next action depends on the
observed values; no threshold tuning, automatic release or further matches are
authorized by this plan alone.
