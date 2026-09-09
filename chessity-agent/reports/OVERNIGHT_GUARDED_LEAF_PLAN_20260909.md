# Guarded rule-aware leaf evaluation, declared before runtime tests

The pawn-mask runtime passed exact-work efficiency at 1.532x aggregate CPU
throughput and higher mean timed depth. Its clock-choice review still failed:
round70 move15 preferred Qa5 at depth5 where the shallower control chose Bb4;
round72 move9 also had more occurrences of the inferior pawn recapture. Preserve
that failure. Speed exposes the position evaluator's remaining weaknesses.

The frozen 781x64 rule-value model reduced error on the new D65 descendants from
190.84 to 169.79cp overall, but middlegame error improved while endgame error
worsened. The original failed fit remains failed. This candidate changes runtime
architecture and how that fixed model is applied; it does not claim new training
or a passed independent strength test from those already inspected data.

Integrate the existing two-perspective piece accumulators with all 13 rule
features: four castling rights, legal en-passant file and normalized draw clock.
Carry fullmove number through make/unmake. Apply a fixed half blend, capped at
300cp correction, only beyond move12 and with non-pawn phase greater than8.
Opening and ending evaluations remain exactly classical. This guard and blend
are declared before the new runtime diagnostics, with no sweep or retuning.

Retain the original search semantics, repetition/mate rules, active trained root
policy and optional Alien preference. Use the pawn-mask runtime's exact attack
and evaluation optimizations. No teacher lookup table, network access or runtime
learning is bundled. The fixed rule-value checkpoint is copied byte-for-byte.

Before benchmarking, verify incremental versus rebuilt feature accumulators and
the NumPy network oracle across legal moves, mirrors, castling, promotion, legal
and pinned en-passant, fullmove/draw-clock changes and restoration. Test exact
classical scores in excluded phases and zero blend. Require a legal bounded
runtime and startup below90seconds.

Then compare four alternating one-second probes on each of the existing22
development roots plus the new D65 mistakes at White23 and Black25/26/35. Require
nonincreasing mean regret at both teacher budgets, no increased major/mate errors
per root, and at least one independently supported100cp repair. Report depth and
CPU cost; this behaviour-changing evaluator has no fixed-node score-parity gate.
Only a pass permits strict read-only validation and the established four-game
practical comparison, followed by clean-win conditional rated pairs. Preserve
all contrary evidence and v1.53; never promote automatically or claim Elo.
