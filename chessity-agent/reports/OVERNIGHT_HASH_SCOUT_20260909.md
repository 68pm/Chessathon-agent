# EP-complete incremental hashes and root scouts on53

This is a distinct combined experiment, not a rerun of failed cycle08/09/PVS
pilots. The new hash implementation removes the full-board fallback for parent
or child raw en-passant squares by carrying the canonical legal EP contribution.
It handles captured en-passant pawns and all promotions/castlings explicitly.
Full position_hash remains an independent oracle and is still used to restore
actual game histories. Repetition context and halfmove checks remain unchanged.

Reuse the project's already tested, unselected root-scout algorithm on53 together
with this new hash mechanism. No geometry prototype, value fit or changed chess
evaluation is included. Full-depth root scores must agree with53 on the bounded
probe; node count may differ because scouts avoid unnecessary full searches.

Before the trial, check legal-child hashes against full recomputation, castling,
en-passant pins/irrelevance, captures and all promotion types. Check root bound,
bonus, mate and interruption behavior with an independent fail-hard oracle.

Use12 existing fully reconstructed development roots, including both new loss
positions. Two persistent workers compile serially under the real90s init limit,
then alternate baseline/prototype/prototype/baseline on each root and budget.
Only one search executes at a time; no repeated JIT between timing blocks.
The worker imports agent before Numba so production platform/diagnostic settings
take effect. Each fixed-depth4 search has2M nodes/12s safety caps; each clock search
has1s. Both use the unchanged move policy and cleared search state.

Require full depth4 (or identical early mate), equal fixed-depth scores, median
CPU speedup>=1.10 and no lower mean clock depth. This permits teacher review of
clock choices and small matches, not an immediate release. Preserve all results
and reject or diagnose failures without unchanged retries. Four-game provisional
selection rule is fixed in work/overnight-20260909.md before games begin.

Geometry01 remains rejected/incomplete: exact586-position evaluation parity,
1.2731 evaluator CPU ratio, but completed full-search comparisons were slower
and the final unchanged baseline import took92.964s, exceeding90s. No claim of
overall speed improvement or stronger play follows from the microbenchmark.
