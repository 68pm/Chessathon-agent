# Bounded quiet defence against a concrete queen-check threat

Declared before implementation and measurements. Bitsets-02 completed176probes:
fixed-work scores/moves/depth/nodes were identical and aggregate CPU speedup was
1.1933, but mean1s depth fell4.4545to4.3636. Reject its combined gate; do not rerun
unchanged or bundle that code. The older E55 battery extension used a geometric
bishop/queen ray. This new trigger tests an actual legal queen-check opportunity,
with the checking queen not currently attacked, rather than that battery pattern.

Start from retained53. At a non-checked horizon with qdepth<=2, allow one full legal
ply if the opponent queen lies within three files/ranks of our king and a bounded
probe finds a safe legal queen check after a hypothetical pass. Copy the rule
state, switch side and clear en passant only in the probe; do not add a null move
to actual history. Consider at most12 geometrically aligned queen destinations in
original move order. Make/unmake each candidate, reject self-check and attacked
checking queens, and restore every board/state slot. This is a threat heuristic,
not a legal game continuation, independent value label, score or mate claim.

One credit per line, included in TT context, prevents repeated defensive expansion.
All legal defensive alternatives remain available in the extra ply. Original
check evasions, near-queen attacking checks, terminal/repetition rules, root policy,
weights, time control and node/deadline bounds remain. No bitsets, rejected value
fit, previous battery extension, aspiration or pruning is bundled.

First check the compiled threat probe against an independent python-chess pass/
queen-check oracle across seeded legal games, explicit safe/unsafe/pinned/blocked
checks and both colours. Verify state restoration, the candidate limit, one-credit
behaviour, TT context separation and unchanged non-search functions. These are
necessary correctness checks; a trigger test alone does not demonstrate strength.

Then production53/prototype warm workers, prototype first,90s startup each,
ABBA1s clock on the same22 exposed development roots. Independent80k/320k teacher
review starts only after workers close. Require at least one>=100cp repair at
both budgets, nonincreasing mean regret at both budgets, no increase in paired
200cp errors or mate losses, legal/restored/on-time choices. No depth-gain gate:
this is an explicitly behaviour-changing defence experiment. Freeze all sources
and roots before measurements; no unchanged failure retry or threshold changes.

A pass permits strict read-only packaging, then the already declared four-game
comparison against53 via feedback_matches at120s+0.5s. Promotion requires>=50%
points, at least one clean win and no candidate operational failures. Conditional
nominal ascent and the07:20report remain as declared in the overnight journal.
Learning weights remain fixed for this causal search test; failed descendant fit
and separate feedback checkpoints remain experimental. Existing verified field
mistakes provide targets, so no additional broad game download is needed.
