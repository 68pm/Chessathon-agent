# Complete recursive signature coalescing

Declared before new implementation/measurement. Explicit-search-01prototype
initialized in80.574s with TWO search variants, differing only in qdepth:
Literal[int](0) versus int64. The baseline then exceeded90s, so no probes ran.
Keep that incomplete trial. Root-only widening left three recursive scout/
re-search calls supplying literal zero, which still generated the other kernel.

New minimal mechanism: retain the explicitly typed root boundary and widen the
three recursive qdepth=0arguments to np.int64(0). All numerical arguments, search
logic, weights, evaluation, clock and root policy remain unchanged from53. No
defensive extension, bitsets, classical specialisation or failed learning is added.
Normalize these casts in the AST to verify complete semantic-source isolation.
Add a real compiled recursive-zero diagnostic; record actual engine variants.

Use the same predeclared startup-oriented method in a fresh run:22roots,176ABBA
probes,250knode/12s fixedwork plus1s clocks, prototype thenbaseline90s starts.
Require exact fixedwork parity/completion, nondecreasing mean clock depth, and
either>=1.10aggregate CPU ratio OR>=20%startup reduction with CPU ratio>=.98.
The real one-variant hypothesis is diagnostic, not presumed from the toy test.
No unchanged retry, threshold relaxation or suppression of the prior failures.

After a pass: independent clock-choice review, strict read-only package check,
four feedback_matches games versus53, then conditional nominal ascent under the
existing frozen short-match rules. Startup improvement alone is not stronger chess.
