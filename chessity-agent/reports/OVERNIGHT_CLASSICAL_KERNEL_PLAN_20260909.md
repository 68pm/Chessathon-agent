# Specialise the selected search kernel before adding more complexity

Declared before implementation or measurements. Qcache01 preserved fixed-depth
scores but delivered1.08556x aggregate CPU speedup, below its1.10gate; its89.19s
startup also left little room below90s. It is rejected and is not bundled here.

The selected53 uses zero leaf-value blend, yet its recursive search still passes
neural arrays and compiles conditional accumulator updates and value readout.
Create a separate classical-only recursive kernel from exact53. Remove only
disabled leaf-value arguments/branches and call the existing classical evaluator
directly. Preserve ALL active root-policy weights and bonuses, opening preference,
time manager, classical terms, search windows/order/reductions setting, check limits,
mate/draw rules and history context. Keep the public root interface and reject
nonzero leaf blends explicitly, rather than silently ignoring a future value model.

This is an exact optimisation of the currently selected configuration, not a new
evaluation or a removal of the trained root move policy. No data or model is fitted.
The separately preserved general evaluator remains available for future learned
value candidates after their gates pass.

Cheap independent tests cover policy bonuses/mate ordering, interrupted root
restoration and rejecting unsupported blends. Then two production imports serially
under90s; ABBA per each of the same22 development roots. Fixed250,000-node probes
(12s guard, depth64) must match nodes, completed depth, score and chosen move exactly.
Also run1s clock probes, one worker at a time. Preserve any failed run unchanged.

Gate fixed before results: exact fixed-work parity and completion; no lower mean
clock depth; and either>=1.10x aggregate fixed-work CPU speedup OR>=20% lower startup
time with aggregate fixed-work CPU ratio>=0.98 (2% tolerance for timing noise).
Both imports must pass90s. Report all CPU/wall/startup results, not only the branch
that passes. A startup reliability gain can be useful even without a major speedup.

If passed, independently review the clock choices at80k/320k after both workers
exit. Require non-increasing finite mean regrets and no added paired major/mate
regressions. Then read-only validation, four games against53 throughfeedback_matches
under the already declared promotion rule, and conditional rated colour pairs.
No promotion, new version number or Elo claim before those practical checks.
