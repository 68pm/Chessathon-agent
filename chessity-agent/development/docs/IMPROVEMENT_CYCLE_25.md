# Cycle25: prioritize direct checking moves without changing search values

The completed cycle24 full-window diagnosis reproduced the rook preference
at depth5; the check-extension prototype preferred a better move at depth6.
This motivates spending search work more effectively. Keep cycle23's two
check-extension credits, but test a cheap direct-check priority among otherwise
quiet moves. No new evaluation, training weights, quiet-check generation,
aspiration, pruning or time management is bundled.

Detect attacks from the moved piece's destination using mailbox geometry and
unblocked rays, without making a move or mutating the board. This is an ordering
hint only: discovered checks and castling checks remain fully searchable through
unchanged move generation. Existing transposition, capture/promotion and killer
priorities remain above this category. Direct quiet checks score700000 plus at
most99999 history points, above ordinary history's500000 cap and below killers.
Pass the known enemy king square from state to avoid another board scan.

Ten focused correctness cases precede measurements: independently compare direct
checks with python-chess moved-piece attacks over240 deterministic legal positions;
check priority and array preservation on all17 audited roots; compare exact
completed depth3 full-window scores with the frozen23 parent on six roots,
including the king and rook targets; check terminal precedence and interrupted
state restoration. Search tests have1M nodes per build/root; preserve any failure.
Board histories and all passed parent extension evidence remain available.

The performance gate remains the original cycle23 rule, evaluated against
selected51: all17 one-second clock roots plus three250k-node/8second diagnostics
per build, root policy disabled equally, exact histories and cleared state.
Init<=90s, outer clock<=1.25s and node probe<=8.25s. Each subprocess has a300second
owned-process-tree timeout, including the Windows venv child. Guard at least
2048MiB disk/768MiB RAM before every heavy process, max20minute wait, serial CPU
work, hidden Normal-priority execution and respect STOP flags.

Require fewer repeated original clock mistakes and avoidance of Kf1 in at least
one king probe. Only if this cheap gate passes, review20choices/build at80k/320k
teacher nodes using existing references and a frozen copy of cycle23's choice
cache where compatible; maximum16M new nodes before cache. Require lower clock
mean regret at BOTH budgets, no newly stable paired200cp error or mate loss in
either mode, and a king choice within50cp at both budgets. The already losing
rook position receives no exemption. Do not change criteria after outcomes.

Pass permits strict read-only packaging then exactly two120+0.5 games against51
from unused prepared opening index6, both colours, requiring at least50% score
and no candidate operational failure before further selection. No automatic
promotion or Elo claim. A failed gate leaves selected51 unchanged; no timing
retry, long consistency study or matches until a win.

Engine efficiency is the first need. Learning remains fixed: future correction
targets must include verified opponent replies, fit the runtime residual cap and
survive matched controls. Data comes from the existing17 audited mistakes,
histories and teacher analyses; no broad GM download or repeated failed fit.
