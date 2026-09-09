# Complete the legal-existence allocation optimisation

Start from exact selectedv1.56. Its main search already reuses move and ordering
arrays, but its full legal-existence check still allocates another move array at
each quiescence node. Reuse the same ply's move buffer before any live search list
is generated. Preserve the full generator, move order, rule checks and evaluator.
This differs from the rejected fast king-step legal-generation shortcut: no
legal-generation algorithm or visitation order changes.

Keep root policy and Alien preference unchanged for this isolated measurement.
Test python-chess legality, mates/stalemates, castling, promotion, en passant,
board restoration, row ownership and bounded storage. Compare exact fixed-work
move/score/depth/node parity in warmed ABBA runs. Require at least5% median and
aggregate CPU gain and no reduction in mean one-second depth before progression.
Use six current field starting boards and six preserved tactical/defensive roots.
These are development checks, not independent playing-strength evidence.

Only after the fresh game review completes and its workers close should the
tests/benchmark run. Independently review timed decisions before any short game
screen. No new selected release follows from speed alone. A separate opening
preference ablation and labelled descendant curriculum may follow the four-step
order, with their own evidence; do not silently bundle untested changes.
