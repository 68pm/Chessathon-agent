# Bound early quiet-check work to complete defensive root iterations

Both speed prototypes failed. Hash/scout02 completed96 probes with median CPU
ratio1.0 and unchanged mean clock depth4.4167. The latest loss at24 was the only
fixed-depth discrepancy: most12s probes hit the safety clock atdepth3, while one
prototype completeddepth4. This is incomplete fixed-depth evidence, not proof
of different minimax values at a matching depth. Both imports passed.

The late round72 root exhausted over1M nodes in12s and sometimes failed even to
complete depth1 at1s. This supports reducing the early forcing-continuation cost
so the search can examine defensive alternatives across the legal root moves.

One original53-only change: root iterations1 and2 pass two quiet-check credits;
depth3 and later restore the existing four credits. Captures, promotions, all
check evasions, checking-node extensions, mate/draw rules and the recursive search
code stay unchanged. Quiet-check budget already belongs in TT context. Do not
bundle rejected geometry, hashes, scouts, evaluation or trained weights.

Six or more independent tests check root credit selection, restoration and AST
identity of the recursive search. Then use two serially compiled persistent
workers with production startup<=90s. ABBA one-second search on12 recent roots
plus the four rated52 controls, including the bishop sacrifice previously fixed
by53. All histories restored; root policy enabled in both builds. No extra trials
or changed parameter values after seeing outcomes.

After both workers exit, independently review all selected moves at80k/320k with
the existing actual-history teacher cache. Require at least one100cp paired
repair, no increased counts of200cp errors/mate losses in any root, non-increasing
mean finite regret at both budgets, and at least one extra completed ply on the
motivating round72move24 root. The gate permits read-only validation and a short
comparison through feedback_matches; it does not create a release or Elo claim.

This implements the second priority, useful move selection/defensive search.
Position-value fitting remains a separate later stage with independent labels.
