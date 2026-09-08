# Separate the canonical runner from added diagnostics

At07:47 BST both resource guards recovered. The unchanged plain-startup candidate
then passed strict read-only validation: initialization61.531seconds, two legal
120000ms calls, maximum3.487seconds, peak232681472bytes. Its subsequent
instrumented protocol probe crashed during initialization after35.554seconds.
The log contains a30-second stack dump and a native access violation during
Numba type conversion. The Colorama-specific option did not eliminate this
instrumented-probe failure. Preserve both outcomes; no candidate promotion.

The probe uses a runpy launch wrapper and periodic faulthandler stack dumping.
Those additions are absent from harness.sandbox.local and the actual runner.
Python documents that periodic dumps use a watchdog thread; this establishes
an instrumentation difference, not that the watchdog caused our crash.
See [Python 3.12 faulthandler documentation](https://docs.python.org/3.12/library/faulthandler.html#dumping-the-tracebacks-after-a-timeout).

Next execute exactly one request through the existing harness.sandbox.local,
without the added launch wrapper or stack timer. Keep the same frozen candidate,
90-second initialization allowance, C58 position and120000ms request. Record the
exact command, hashes, available resources, raw exit code before cleanup and
stderr. This is a diagnostic of a changed launch path, not another unchanged
strength test. A pass would show that this canonical request worked under those
conditions; it would not prove the sole cause of earlier failures or establish
reliability across many launches. A failure requires inspecting that result before
further chess matches. No ordinary games or automatic promotion are scheduled.

Engine priority: establish actual runner behavior. Learning priority: preserve
weights while isolating startup. Data priority: current process evidence is
sufficient; no new game collection or fitting is useful for this distinction.

The canonical request passed at07:53 BST: initialization50.292seconds, legal
`c4b5` in5.020seconds, total55.321seconds, no stderr output. All frozen candidate
hashes were unchanged. This permits a small real-game operational check; it does
not establish that instrumentation was the sole cause of the earlier crash.
