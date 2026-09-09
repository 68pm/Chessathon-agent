# Original bitset-assisted attack detection

Declared before implementation or measurements. The preceding classical-only
kernel passed strict read-only package validation(76.278s startup), but its paired
trial never tested the prototype because the53control exceeded90s. Preserve that
incomplete trial. This is a new combined candidate: the same zero-leaf-value
specialisation plus bitset attack detection. Neither is presumed stronger.

Preserve0x88 move generation/order and all classical values, trained root policy,
clock, check limits and draw semantics. Extend the board array from128to142signed
64-bit slots:13piece bitsets and all occupancy. Maintain them for every square
write in make/unmake and the temporary legal-en-passant hash check. Capture tuple
right-hand values before applying changes. The existing legal-pawn proof changes
no board squares. Reject a legacy board lacking metadata instead of reading past
its allocation. All existing evaluation/hash loops must ignore metadata slots.

Precompute pawn/knight/king attacker masks and eight rays. Identify the nearest
occupied square on a ray using lowbit or native leading-zero count, then test the
appropriate enemy sliders. This is our own geometry/implementation, with no
external engine code, weights or lookup labels. Use the documented Numba intrinsic
API and LLVM bit-count primitive through its builder, without a new dependency.

Correctness: compare every square/colour against python-chess attack detection
across seeded legal games and explicit special positions; verify all legal-child
states, bitsets and hashes, including pinned/legal/irrelevantEP, captures,
castling and all promotions; long make/unmake restoration; known perft counts;
bit63/zero leading-zero semantics and rejecting old arrays. Run compiled helpers,
not only source/mocked tests. Do not edit frozen results after measuring.

Then a fresh production pair, prototype import first to establish that this new
kernel can run, each under90s and within capacity. Both stay warm; only one searches.
ABBA across22 existing development roots at250knodes(12s guard/depth64) and1s clocks.
Require exact fixed-work nodes/depth/move/score parity,>=1.10aggregate CPU speedup,
and no lower mean clock depth. Report startup and all timings; startup alone does
not pass this new attack-detection gate. No unchanged failed-pair retry.

If passed, independently review clock choices, validate the final read-only ZIP,
then four games versus53 throughfeedback_matches before provisional promotion.
Keep every result and conditionally ascend2400/2600/2800/3000 only after clean wins.
No new neural fit, broad game download or rejected Qcache/pruning change is bundled.

API references: [Numba extension API](https://numba.readthedocs.io/en/stable/extending/index.html),
[IRBuilder bit-count primitives](https://llvmlite.readthedocs.io/en/latest/user-guide/ir/ir-builder.html).
