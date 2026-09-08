# Completed bounded check-extension pilot

**Selected upload remains v1.51.** The two-credit check-extension prototype
failed its predeclared tactical gate. This exposed development sample does not
establish a playing rating. No new trained model or numbered release is created
by this report.

| Diagnostic | Selected v1.51 | Check-extension prototype |
|---|---:|---:|
| Repeated original errors, 17 one-second roots | 14 | 12 |
| King-root move, one second | g1f1 | g1g2 |
| King-root move, 250k-node diagnostic | g1f1 | g1g2 |
| King-root completed depth, node diagnostic | 7 | 6 |
| Initialization | 70.537s | 74.627s |

The king decision improved from Kf1 to Kg2 in both probe modes, with zero
regret at both teacher budgets. Mean clock-root regret fell from
349.41/383.82cp to
270.59/293.88cp.
However, the clock probe at40Rc8 regressed from Rd3 (64/68cp regret) to
Rc8 (283/284cp). That newly stable error violates the predeclared rule, even
though the position was already losing. The node-limited prototype instead
chose Nd5 (138/117cp), so the remaining decision is sensitive to search budget.
There were no newly detected mate losses. Retain the useful king-defence result
while diagnosing this regression; the acceptance rule remains unchanged.

All 40 position probes produced legal moves with restored state and met their
time bounds. 6
of the six node diagnostics reached the full 250k-node limit; these are reported
separately from the clock measurements. The gate requested 2,800,000 new
teacher nodes. No parameter fitting or ordinary matches ran in this pilot.

The first correctness run preserved eight passing compiled checks and two failed
Python observer cases. Those observers bypassed the compiled uint64 argument
boundary and raised OverflowError. Only their context conversion was repaired;
both corrected cases passed in 17.04 seconds. The original XML, source and logs
remain available. Engine code, roots, budgets and acceptance criteria were frozen
throughout; already passed checks were retained by their evidence hashes.

Engine work tested extra depth for forcing checks, prompted by the missed
opponent reply in the preceding trace. Learning weights stayed fixed: the trace
showed that fitting only the student's preferred endpoints misses adversarial
continuations. Targeted data came from the same 17 audited mistakes and their
preserved histories; no broad download was needed.

The prototype is rejected under the original rule. Preserve v1.51 and diagnose the remaining error before another change; do not replay this unchanged pilot.

[Original gate](IMPROVEMENT_CYCLE_23.md) ·
[Observer correction](CHECK_EXTENSION_CREDIT_TEST_RECOVERY.md) ·
[Complete evidence](evidence/check-extensions-20260908/manifest.json) ·
[Gate result](evidence/check-extensions-20260908/cycle-23-credit-checks/gate.json) ·
[Preceding diagnosis](KING_DEFENCE_DIAGNOSIS_20260908.md) ·
[Selected agent and game results](IMPROVEMENT_RESULTS.md)
