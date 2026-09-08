# Cycle 33: identify the missed defense after Qe3+

Predeclared 8 September 2026 before analysis. No code or model change.

Cycle 32 showed that the student's imagined Kh1 continuation after Qe3+ is
actually winning for Black. The missing defensive decision is a new diagnostic
position. Legal inspection finds exactly three replies: Kh2, Kh1 and Rf2.

First, independently score the position and ALL three legal replies with
Stockfish at 80k and 320k nodes, reusing the unrestricted best analysis when
its first move matches. Maximum 1.6 million requested teacher nodes. Retain
all lines, finite/mate scores and exact history; do not select positions by
whether a preferred hypothesis works.

Then one unchanged v1.52 production process examines each reply at 3 and 5
plies including the reply, with zero remaining check-extension credits. Depth3
matches the remaining nominal horizon in the cycle32 continuation; depth5 is
a separately identified descendant diagnostic, not a repeated root gate.
Each forced search is bounded at250k nodes/4seconds, initialization90seconds,
six attempts total <=1.5 million student nodes. Preserve exact TT continuations,
their stop reasons, leaf static values, complete history/state and interruption
status; incomplete scores are null. Compare teacher and student from White's
perspective, identifying how the defender alternatives are ranked.

Engine diagnosis is first priority. Learning must include the stronger opponent
counterfactual rather than reinforce the student's favorable imagined leaf.
These three legal replies are sufficient targeted data; no broad download,
new game, neural fit, package, acceptance threshold change or Elo claim.

Freeze all files before execution. Teacher and student are serial, with both
2048MiB disk and768MiB physical RAM checked before every heavy process, capacity
waits at most20minutes, both STOP flags honored. Hidden Windows System PowerShell
task at Normal priority4 from launch; each owned worker tree bounded360seconds.
Publish every outcome and use the result to select the next general engine or
compatible value-learning change. No automatic promotion or rerun.
