# Combined search work reduction, declared before measurement

The isolated bitset attack kernel improved aggregate fixed-node CPU time by
19.3% but lost a small amount of average one-second depth. The conservative
quiet-check prefilter preserved fixed-node choices and improved average depth
but gained only 7.4% CPU time. Neither qualified individually.

This is a new composition of those independent mechanisms: bitsets make retained
attack queries cheaper; the prefilter avoids unnecessary reversible board and
metadata updates for moves that cannot be quiet checks. Use the compiler-repaired
v1.53 control to avoid redundant compilation in both sides. The classical-only
kernel removes unused leaf-network arguments; trained root-policy weights remain
active and unchanged. No new pruning, search credits or evaluation values.

Before measuring, run both independent compiled correctness suites against this
actual combined core, including special moves, high-bit masks, legal move sets,
hash restoration, perft, and conservative check coverage. Frozen source hashes
include the reused tests and runner. The new candidate is frozen before games.

Use the same 22 exposed development roots and 176 serial ABBA probes. Require
both startups below 90 seconds, exact fixed-node move/score/depth/work parity,
aggregate CPU speedup at least 1.10 and nondecreasing mean one-second depth.
No startup-only alternative. Do not run this benchmark or compiled tests while
the development games or their feedback workers are active.

Only if passed, use overnight_matched_screen for independent Stockfish review
of clock choices, strict read-only validation and the small practical comparison.
All previous failed gates remain failed. This composition does not establish
strength without those further checks and does not change the selected upload.
