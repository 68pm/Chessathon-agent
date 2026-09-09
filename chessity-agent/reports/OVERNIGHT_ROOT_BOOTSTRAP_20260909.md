# Bounded first-depth bootstrap and completed-child fallback

The classical-countercheck integration failed: in round72move24 its first full
iteration did not complete, and the driver returned the first generated legal
move. Inspection also found that root_iteration discarded already completed
root children when any later child hit the deadline.

Make one new candidate from that frozen failed trial. Retain the same engine,
evaluation, policy, countercheck budget and compiler. Before ordinary iterative
deepening, spend at most5% of the total move time, capped25ms and4096nodes, on a
depth1 capture/evasion search with zero optional quiet-check credits. This is a
bounded move-ordering/fallback seed, not a completed full-search depth. Count its
nodes and elapsed time against the original move allowance. Keep TT score
contexts distinct through the existing quiet-budget key. Then run the original
four-credit iterative search within the original hard deadline.

On an interrupted root iteration return the best COMPLETED child's move/score;
use it only if no full depth has completed. Never use an interrupted child score.
Preserve the previous completed iteration on deeper interruption. If no child
completed, retain the legal fallback and report depth0. No invented completed
depth, longer clock, new leaf labels, fit or result-conditioned rewards.

Verify node/deadline sharing, first-iteration fallback, retention of a completed
deeper result, legal board/history restoration, root-child interruption, and the
existing17 classical/countercheck tests. Repeat the108 ABBA1s diagnostic for this
genuinely changed candidate. The existing startup<=65s, regret/major/mate/repair
gate and conditional small feedback match screen remain unchanged. No new
selected version without evidence; deadline06:40BST and report07:20BST remain.
