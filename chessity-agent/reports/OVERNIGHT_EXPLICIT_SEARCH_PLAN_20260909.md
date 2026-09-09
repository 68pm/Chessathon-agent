# One compiled search signature at the root boundary

Declared before implementation/measurement. Queen-defence-01 passed15checks but
exceeded90s prototype startup, before any probes or baseline initialization. Keep
that failure. Two small real-Numba diagnostics exposed a mechanism: omitted
recursive defaults can create multiple compiled signatures. With changing credits,
the diagnostic compiled three signatures (omitted, mixed literal, generic), while
an explicitly widened boundary compiled one. This is a hypothesis about the real
engine, which must report its actual signature counts and startup time.

Make a minimal change to pure retained53: at root_iteration's call into search,
pass alpha=-31000, ply=1, qdepth=0 and extensions_left=2 as np.int64, and explicitly
pass np.int64(4)/np.int64(0) for the existing quiet-check and attacker defaults.
Preserve every value and all other code, including the search body, root policy,
neural weights, evaluation, move ordering, terminal rules and actual clock.
Do not bundle bitsets, classical specialisation, the failed defence extension or
any failed fit. No new chess heuristic is introduced.

Validate AST isolation and exact root-call values, policy/mate ordering and abort
restoration using independent root oracles. Include the real compiled dynamic-
default diagnostic. Then prepare frozen prototype and production warm workers,
prototype first,90s startup each, logging actual search signature counts. Reuse
22fixed development roots:250knode/12s bounded fixedwork and1s clocks,ABBA.

Require fixed-work nodes/depth/move/score parity and completion, nondecreasing mean
clock depth, and either>=1.10aggregate CPU speedup OR>=20% faster startup with
CPU ratio>=.98. This startup-focused alternative is declared now for a distinct
compiler mechanism; it does not change the failed bitset gate or retry that code.
Keep every measurement and do not rerun an unchanged failed pair.

Only a pass proceeds to independent80k/320k review of clock choices, strict
read-only validation and four feedback_matches games against53 on the frozen
short starts. Require>=50%points, one clean win and no candidate operational
failure before a provisional release. Rated pairs ascend after actual wins.
No calibrated Elo or higher playing strength is implied by reduced startup alone.
