# Guarded leaf cache-context correction

Preserve guarded-leaf-01 as a rejected preflight. Its new evaluator uses fullmove
number to activate beyond move12, while its transposition value context omitted
that state. An isolated cache-probe regression reproduced score reuse across the
activation boundary. No game or ordinary benchmark was run for that draft.

guarded-leaf-02 adds min(fullmove,13) to the history-sensitive transposition value
context. Distinguish every pre-activation move number because deeper descendants
can cross the boundary at different depths; all move13-and-later states share
the same already-active bucket. Draw-clock, repetition, extension and quiet-check
contexts remain in place. The same regression must now cause a fresh search.

All other declared architecture, blend, phase guards, copied model parameters,
26-position practical quality gate and release requirements remain unchanged.
The frozen first draft, its preparation, import-order lint warnings and failing
preflight log are retained. This corrected source is a separate bounded attempt.
