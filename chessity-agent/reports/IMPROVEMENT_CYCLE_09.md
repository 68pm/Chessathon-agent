# Cycle 09: capture ordering pilot

Base: frozen v1.41 (compiled-qsearch-endgames-v1). Existing confirmed failure
game-013-ply-056 chose Rxd6 and lost the exchange to ...Rxd6. Current ordering puts
every capture before quiet defences, regardless of the material recapture chain.

Implement one bounded change: a legal least-valuable-recapture heuristic to demote
negative exchanges below quiet moves at search depth 3 or greater. Keep checking
captures and the transposition hint at their existing priority. No pruning, changed
evaluation, retraining, root policy change or new downloaded data in this pilot.
This heuristic is an approximation; it is not a tactical proof and must never
discard a legal move. Preserve v1.41 and work in a separate prototype.

Validate board/state restoration, legal pins and kings, en passant, promotions,
and poisoned captures against a python-chess oracle, plus search mate and node
budget checks. Use the eight already verified v1.41 200cp errors as development
roots: both variants get 500k nodes (20s safety cap) and one 1s clock probe. Count
all roots, not just the motivating failure. Root policy is disabled equally by
the existing probe. These are exposed diagnostics, not strength confirmation.

Proceed to a small 2–4 game comparison only if correctness passes, error repeats
decrease, and verification of the newly chosen moves at 80k and 320k teacher nodes
shows no added forced mate losses and lower mean capped regret at both budgets.
No unchanged retries after a failed gate. Runtime performance can reject an idea
even if it looks conceptually attractive. Use current quick-check phase evidence
and authenticated recent competition games to select the following experiment.

Three priorities: first test this search mechanism; defer learning until a useful
search improvement or a measured evaluation gap; reuse current verified targets
before collecting more data. No heavy pilot computation during timed matches.


Completed: rejected without a new release or ordinary matches. All ten correctness
tests passed (one invalid test fixture was corrected before the final run; both
test reports are preserved). At 500k nodes both builds repeated all eight old
errors, with mean completed depth 6.5. Under the fixed one-second budget the
baseline repeated six errors and the prototype eight, so the cheap gate failed.
No teacher verification or fitting followed. Do not rerun this unchanged idea
or lower its gate. The selected v1.41 ZIP remains unchanged.

The engineering mechanism was implemented and measured; it did not improve the
target decisions. That gives no reason for another network fit. Existing data
was sufficient to reject the idea without new downloads or teacher calls. The
next diagnosis uses the latest actual competition games with version provenance,
now accessible after sign-in. Original predeclaration is preserved in the evidence.
