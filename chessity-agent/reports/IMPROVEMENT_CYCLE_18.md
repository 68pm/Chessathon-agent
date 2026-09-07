# Cycle18: finish startup compilation before announcing readiness

The selected driver uses a60-second search deadline for its one-depth startup
warmup. Its legal-move setup can itself trigger compilation before the iterative
search checks that deadline. If setup consumes more than60seconds, the loop exits
without ever compiling root_iteration; warmup returns and the agent announces
readiness. The first match move then has to compile that missing path on its clock.

A simulated70-second setup deterministically reproduces the skipped root call in
the unchanged41 driver. The startup-only candidate unconditionally permits the
one-depth warmup, with the existing4096-node cap. The external90-second startup
watchdog is unchanged: a slow initialization must fail there rather than pretend
to be ready with missing compiled code. This corrects a demonstrated possibility;
the previous background matches did not log signatures, so it is not proven to
explain their timeouts.

Candidate `candidates/compiled-startup-complete-v1` changes only
CompiledSearch.warmup. The game-time search, clock allocation, evaluation, policy,
weights and endgame tables are identical to41. Three focused checks passed: normal
setup, delayed setup that skipped the original root, and exact AST parity of all
driver code outside warmup. The node/depth caps remain1 and4096 respectively.

Engine need: reliable readiness is required before useful defensive search can
matter. Learning need: leave all weights unchanged while isolating this operational
fault; the previous failed replay fit is not repeated. Data need: the simulated
delay and existing first-response failure are sufficient to motivate this fix;
new games or GM data cannot repair a startup control-flow error.

Next run the same read-only90-second initialization and two120000ms legal-move
checks. Preserve all failures. If they pass, this can be archived as a startup
reliability revision, with no claimed Elo increase. Do not attribute an isolated
pass to all hardware or hide the earlier failed matches. Before changing the
recommended upload, verify its protocol initialization and response under the
actual local runner as well. Resolve background test reliability before further
nominal2800/3000 game spending. The aspiration search pilot remains separate.

Read-only preflight passed on7September23:32BST: initialization42.105seconds,
peak working set230436864bytes, two legal120000ms calls, maximum3.486seconds.
Filesystem mutations, network and subprocess access were blocked; optional Alien
preference and elementary tables were exercised. ZIP SHA256:
`3fcbed565383eb5817d426826dcf2731842a2606c74943ba988e8681eec29660`.
This is an unnumbered candidate pending the actual protocol check, not yet the
recommended download or evidence of higher playing Elo.
# Background protocol outcome

The strict package check passed, but the subsequent background protocol probe
failed initialization after90.298seconds with no chess move. Its stderr contains
a native access violation while Colorama probes/converts Windows console handles
during Numba diagnostics. Preserve `cycle-18/protocol/report.json` and `stderr.log`.
This candidate is not promoted. Cycle19 tests the supported plain-diagnostics
option as a separate change. This trace does not establish the cause of all
previous startup failures or any Codex application crashes.
