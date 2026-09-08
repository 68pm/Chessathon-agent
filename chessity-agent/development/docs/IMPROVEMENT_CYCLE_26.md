# Cycle26: combine check extensions with the verified pawn legality shortcut

Cycle25 direct-check ordering failed its cheap gate:13/17 original clock mistakes
for both builds. Preserve that result and omit its ordering code. Cycle23's two
check extensions repaired the king decision but needed more useful depth at the
rook root. Cycle24 confirmed that the better preference appears one ply later.

Combine only the frozen23 search with the existing48 pawn-legality shortcut.
The shortcut was previously verified against1500 random legal boards and special
cases, and preserved exact fixed-work moves, scores, depths and nodes while
reducing runtime. Its earlier two-game pair failed the practical promotion rule;
those games remain preserved and are not repeated. This is a new combination,
not promotion of48 or a claim that its old timing transfers to this build.

Copy exactly48's has_legal_move function. When a quiescence node is already known
not to be checked, pass checked=False: an empty one-square pawn push from a pawn
unaligned with its king proves at least one legal move. Otherwise use unchanged
complete generation/make/unmake. All other call sites retain checked=True and
the fallback. Validate unchanged helper dependencies and source AST. Keep23's
extension budgets and transposition context; no ordering, evaluation, network,
clock, pruning, aspiration or quiet-check generation changes.

Retain the nine original pawn-proof checks through their XML hash and exact
donor function/dependency parity, without rerunning those unchanged tests.
Run six NEW interaction tests: full-window depth3 searches at six audited roots
must exactly match the23 parent in score AND node/interrupt counters, with full
history and board/accumulator restoration. Each call is limited to1M nodes.
These include the king and rook targets. Preserve all outcomes.

Then apply the original23 tactical rule against selected51:17 one-second clock
roots and three250k-node/8second diagnostics per build, policy disabled equally,
full histories and cleared search state. Init<=90s; outer clock<=1.25s and
node probe<=8.25s; each subprocess<=300seconds with only its own Windows process
tree killed on timeout. Guard2048MiB disk/768MiB RAM before each heavy process,
max20minute wait, hidden Normal-priority serial execution and respect STOP flags.

Require fewer original clock-error repeats and avoid Kf1 in at least one king
probe. Only then review20choices/build at80k/320k, at most16M new teacher nodes
before compatible cached records. Require lower clock mean regret BOTH budgets,
no new stable paired200cp error or mate loss in either mode, and a king choice
within50cp at both budgets. The losing rook position receives no exemption.
Criteria are fixed before results, with no unchanged timing retry.

A full pass permits read-only packaging and exactly two120+0.5 games versus51,
unused prepared opening index6, both colours, at least50%score and no candidate
failure before selection. No automatic release, Elo claim or long study.

Engine efficiency remains first. Learning stays fixed until an objective using
verified opponent continuations can work within the residual cap and beat a
matched control. Existing diagnosed roots, histories and teacher references
supply the targeted data; no broad collection or repeated failed fit is needed.
