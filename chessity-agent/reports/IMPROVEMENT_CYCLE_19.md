# Cycle19: plain diagnostics for a piped Windows runner

The startup-only candidate passed the separate strict package check but failed
its actual background protocol initialization at90seconds. Its captured stack
showed compilation followed by Colorama's Windows console probing, then a native
access violation in the console-conversion path. This is more specific evidence
than the earlier memory-pressure observation. Do not assume every previous failure
had this cause, or claim an engine strength increase from fixing it.

Create a separate candidate, `compiled-startup-plain-v1`, from the preserved
startup-complete candidate. Before importing Numba, set its supported
`NUMBA_DISABLE_ERROR_MESSAGE_HIGHLIGHTING=1` option. Numba's installed source then
chooses NOPColorScheme and does not initialize Colorama's console conversion.
Errors and warnings remain visible as plain text. Merely setting the existing
default `NUMBA_COLOR_SCHEME=no_color` would still initialize Colorama.
See the [official Numba environment-variable reference](https://numba.readthedocs.io/en/stable/reference/envvars.html#numba-disable-error-message-highlighting).

Engine need: avoid a native diagnostic/console failure before gameplay. Learning
need: retain identical weights and chess decisions while testing this environment
interaction. Data need: the recorded protocol stack and an isolated check that
forbids Colorama initialization directly target the fault; more PGNs are irrelevant.

Keep the previous candidate, its passed package check and failed protocol report.
Only the new agent-local environment assignment changes relative to that candidate;
no machine-wide settings or unrelated apps change. Verify AST parity, plain error
output without console initialization, strict readonly package behavior, then one
actual protocol request. No nominal games until protocol reliability is restored.
Do not promote a candidate simply because its offline import succeeded. The
aspiration pilot is separate and must complete its declared gates.

Before launching this plan, the earlier aspiration controller exited with a
separate, explicit `OSError: [Errno 28] No space left on device` while saving its
first baseline probe. Its output was zero bytes; no usable position gate result
exists. The source, logs and failed controllers remain preserved. The new plan
therefore has no successful-prerequisite claim about that failed controller.
It first runs the small diagnostic tests and packages the candidate, then waits
for at least2048MiB free disk and768MiB available physical memory before heavy
validation. The guard waits at most20minutes and does not alter other apps,
pagefile settings or user files. No new games are queued by this plan.
