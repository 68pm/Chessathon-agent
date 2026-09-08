# Bounded labels and a local residual-learning candidate

Two implemented heuristics failed the frozen17-root gate. Preserve their
outcomes. Do not merge them or tune their thresholds. Both probes also exposed
depth-dependent choices: the faster runs often repeated mistakes at greater
completed depth. This is evidence to inspect leaf values, not proof of one cause.

Diagnose unchanged53 at four actual-history roots:20...Qxc6/bxc6 in the2400
loss;15...Nc3/Nb6 in the2600 loss;35.Bc1/c5 and79.Rd7/Rf7/c8=Q in the draw.
Nine full-window depth6 branches, each500k nodes/8s; incomplete values areNULL,
never used as successful scores. Preserve exact-table traces or explicit partial
stops. Add teacher counterfactuals at4/8 plies from both80k/320k root analyses.
At most60 distinct history-aware descendants; each nonterminal q probe100k/2s,
then fresh independent80k/320k value labels, at most24M requested teacher nodes.
The validated27-argument dispatch must not create a new compiled signature.
Serial hiddenNormal4,2048MiBdisk/768MiBRAM before every child,90s init/360s child.

Apply the existing descendant filter: no terminal/mate/in-check/history-sensitive
states, no hidden castling/EP rights, no incomplete q or q-static gap>100cp,
no paired teacher instability>100cp, no duplicated or conflicting piece input.
Keep exclusions. Never copy a root value to a descendant or pretend a favorable
student continuation is the opponent's best defence.

Next bounded learning hypothesis, conditional on enough eligible labels: retain
the768-input/32-clipped-ReLU residual network but initialise its hidden units as
local piece-pattern features around independently labeled quiet descendants.
Activation is max(0,1-HammingDistance/4), zero beyond one piece relocation.
Fit output weights once with ridge regularisation to RAW teacher-minus-current53
values. This local supervision differs from increasing the old global blend.
Maximum32 centres, source-group-balanced selection; retain all raw targets.
The runtime residual cap1500cp accommodates the observed corrections; no target
clipping. Disable the residual in castling/EP, high draw-clock and repeated
positions, which its piece input cannot represent. Use fixed predeclared ridge1,
no hyperparameter sweep or unchanged epoch retries. This is supervised learning,
not outcome reinforcement and not demonstrated generalisation.

Test export/runtime arithmetic equivalence and history guards, then the frozen17
root regression gate. Require reduced paired200cp errors and means at both
budgets, at least one100cp repair, no new paired200cp/mate loss, and legal/restored
timely operation. Retain original labels and teacher budgets for every comparison.
Only a successful candidate advances to read-only validation, a small53 pair,
then the requested2400/2600 games.2800 requires a played2600 win. No long study.
