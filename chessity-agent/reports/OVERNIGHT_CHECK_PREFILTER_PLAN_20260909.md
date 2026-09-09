# Skip provably nonchecking quiet moves before reversible state updates

Declared before implementation/measurement. The matched defence trial completed
88clock choices and22teacher reviews: mean regret rose123.614->146.159cp and
145.818->183.75cp, four roots gained paired-major errors, no100cp repair occurred,
and the critical round72move24fell from depth1to0. Reject the full defensive-ply
extension. Both repaired-compiler builds initialized successfully; the controller
setup now supports an actual causal comparison without the old startup failure.

Use the pure coalesced-search-01control (v1.53search logic/weights with compiler
repair) for BOTH baseline and new prototype parent. Add one conservative geometric
test before make() for quiet, nonchecked quiescence moves. A move may give check if
its destination gives its piece the right attack geometry, or its source aligns
with the enemy king and could uncover a slider. Treat all flagged moves/promotions
as possible checks, preserving castling/en-passant discoveries. False positives
are acceptable; false negatives are not. The check only reads current state.

Keep the complete generated move list and its selection-sort operations unchanged,
so tie order does not change. Skip only moves which the existing post-make check
test would discard. Original legality and actual-check validation remain for all
survivors. No legal checking alternative, capture, promotion, evasion, score,
history, accumulator update, policy or quiet-check credit is removed or changed.
The rejected defensive extension/bitsets/value fit are absent.

Compiled correctness: independently verify every legal checking move is retained
across seeded games and explicit ordinary/discovered/castling/en-passant/promotion
checks, both colours. Check state purity and substantial nonchecking quiet coverage.
Normalize the helper and added guard out of the AST to prove all other code matches
the frozen control. Then fresh22root176ABBAprobes at250knodes/12sguard and1sclocks,
prototype/control90s starts. Require exact fixed score/move/depth/node parity and
completion,>=1.10aggregate CPU ratio, nondecreasing mean clock depth. Startup is
reported but is not an alternative acceptance route for this runtime optimization.

Only a pass proceeds to independent clock-choice review, strict read-only check
and four120s+0.5s feedback_matches games against this compiler-repaired53control.
Label the control accurately; it is not the exactv1.53ZIP. Preserve all prior
failures, require>=50%points/one clean win/no operational failures before considering
a provisional release, and conditionally ascend nominal settings after played wins.
No new training or broad data is needed for this work-removal hypothesis.
