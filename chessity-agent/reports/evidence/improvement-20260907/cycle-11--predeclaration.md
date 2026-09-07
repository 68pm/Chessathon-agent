# Cycle 11: exact static-evaluation cache

Base: frozen v1.41; no cycle09 or10 pruning code. Repeated tactical positions
need more useful search per clock. The static evaluator is a pure function of
the board, side and frozen weights/configuration; it can be reused even when
search-score reuse is prohibited by differing repetition histories.

Add a64k-entry direct-mapped static cache, keyed by the existing full position
hash, with an explicit empty-score sentinel. Allocate it once per root iteration
and pass it through recursion. Keep all move generation, ordering, windows,
terminal/draw checks, search scores, model and policy unchanged. Search-table
history safeguards remain unchanged. A cache miss computes the existing exact
evaluation. Residual blends bypass the cache to preserve floating-point
accumulator rounding; v1.41 uses blend zero. The cache remains memory-only;
no data or runtime disk writes.

Correctness: compare cached and direct evaluation across random legal play,
colliding slots, side changes, empty key zero and multiple residual blends;
verify board preservation and terminal/node-budget behaviour. At fixed250k
nodes on all11 known error positions, require identical completed depths,
scores, chosen moves and node counts. Two passes with alternating build order
measure time: require at least10% aggregate fixed-work speedup across both passes.
Stop on a failed gate; do not run repeated timing trials until one passes.

If passed, require read-only package checks and a two-game colour pair versus41.
Use that small comparison to decide the next bounded step; no automatic claim
of higher Elo and no long independent consistency study. These positions are
development data. Engine efficiency comes first; effective learning and new
targeted data are deferred until this exact optimization is resolved.
