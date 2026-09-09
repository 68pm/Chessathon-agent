# Exact pawn-mask evaluation experiment

The combined attack/prefilter trial preserved fixed-work results and saved 13.94%
aggregate CPU time, but lost average timed depth and remains rejected. This new
mechanism removes three tiny heap arrays and repeated forward pawn scans from
the classical evaluation, using already maintained piece masks. It is a distinct
work reduction, not another measurement of the unchanged failed build.

Pawn file counts are needed only as zero, one, or multiple pawns. Compute that
clamped count from the appropriate file mask. Precomputed forward masks detect
enemy pawns on the same/adjacent files with one bitwise operation. Bishop and
material counters become scalars. Retain every coefficient, phase taper,
conversion option, queen-pressure term and rounded evaluation value unchanged.

Use the compiler-repaired v1.53 control. The prototype also retains the earlier
exact bitset attacks, zero-leaf specialization and quiet-check prefilter. Test
evaluation equality against the original evaluator across both colours, both
conversion settings, random histories, legal child states, promotions and en
passant. Verify make/unmake and evaluation preserve all board/metadata state.

The predeclared runtime gate remains exact fixed-node move/score/depth/work
parity, both startups below 90 seconds, at least 1.10 aggregate CPU speedup and
nondecreasing mean timed depth on the frozen 176 ABBA probes. No startup-only
alternative. Only a pass permits the portable matched quality/read-only/game
screen. Failed previous gates and the v1.53 fallback remain unchanged.
