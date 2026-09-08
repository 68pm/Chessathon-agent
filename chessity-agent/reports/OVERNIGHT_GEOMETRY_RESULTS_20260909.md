# Geometry01: evaluator gain did not translate to a completed search pass

No new release or weights. All586 evaluation positions matched exactly with both
conversion settings. The alternating evaluator CPU microbenchmark ratio was1.2731.

Only three of four full-search workers completed. Their250k-node outputs matched
exactly for all eight roots, including moves, scores, completed depths and nodes.
Against the sole completed baseline, the two prototype runs had median CPU ratios
0.6084/0.7114 and wall ratios0.5809/0.6867. They were slower in those observations.
Mean one-second depths were5.0 for baseline and5.0/4.625 for the prototypes.

The last baseline process imported in92.964s, exceeding the90s startup requirement,
and produced no probes. Its exception and all prior samples remain in the run.
The balanced experiment is therefore incomplete and failed; the partial ratios
must not be presented as a completed controlled speed result. The evaluator-only
gain does not justify a playing-strength claim or replacingv1.53.

The finished task was removed only after verifyingReady/exit1 and no owned engine
processes. The next experiment uses a materially different hash/root-scout
mechanism and imports the production agent beforeNumba; no unchanged geometry
timing retry or acceptance-threshold change was made.
