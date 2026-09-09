# Preserve concrete targets while storage blocks engine work

The v1.56 buffer-descendant controller failed its storage reserve before any
preparation or engine launch. Preserve that failure and the selected release.
Replay the existing higher-budget teacher lines from four already reviewed roots
using python-chess only. Record legal descendants after four and eight plies,
their full histories, exact terminal outcomes, source hashes and game grouping.
Do not launch an engine, import the playing network, fit weights or copy a root
score to any descendant. Every descendant has a null value target and is ineligible
for finite training until separately evaluated and filtered.

Targets: 2600 Black move15, 2400 Black moves24/26, and2600 White move53. The first
two compare quiet defensive alternatives with the played mistakes. The pawn grab
on move26 permits a legal mating continuation, but the better root alternative
was already evaluated as losing. The drawn rook ending was also evaluated as
losing before move53: this is a resistance target, not evidence that a win was
thrown away. Do not punish the draw merely because it was a draw.

This is a bounded preparation step, at most16 teacher-PV descendants from four
roots. They are exposed development positions and do not replace actual student
search continuations or unseen validation. New independent labels, restored
capacity and an isolated value-fit evaluation are still required.
