# Fixed evaluator geometry: new overnight step 1

Exact baseline53. Older incremental hash and capture-order trials failed their
gates; they are not rerun. This trial precomputes the same material/piece-square
base terms and king-ring adjacency currently recomputed inside every evaluation.
No score, root preference, search pruning or network is intentionally changed.

Freeze a seeded legal position corpus and eight existing full-history development
roots before measurement. Compare both conversion flags on the entire corpus.
Run serial evaluator CPU microbenchmarks in baseline/prototype/prototype/baseline
order, excluding JIT. Require exact scores/checksum and at least10% evaluator CPU
improvement before paying for full-search compilation.

Then run the same balanced order with250k-node and1s clock probes on all eight
roots, retaining the original move policy in both builds. Require equal fixed-node
move, score, completed depth and node count; at least5% median CPU speedup with
balanced build order; and no lower mean completed clock depth. Both wall and CPU
measurements are preserved. Host noise still limits small timing estimates.

A passing efficiency gate only permits independent review of changed clock moves,
read-only package checks, and a short practical comparison through feedback_matches.
It is not a release or an Elo claim. A failed gate is preserved without unchanged
retries or weaker thresholds. Existing53 ZIP remains selected.

Single-use source: scripts/overnight_geometry_trial.py.
Results: runs/overnight-20260909/geometry-01.
This step deliberately keeps value learning and field collection for later in the
authorised order; it does not pretend new neural weights have already been trained.
