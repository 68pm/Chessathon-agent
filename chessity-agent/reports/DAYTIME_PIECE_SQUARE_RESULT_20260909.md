# Exact piece-square tables were slower

The isolated v1.55 table prototype passed all twelve correctness tests in 3.95s.
All 96 ABBA probes completed, with exact fixed-work move, score, depth and node
parity. Replacing the original integer formula with lookups preserved behaviour
but did not save time in this compiled implementation.

Aggregate CPU speed ratio was 0.95682 and median ratio 0.96587 (above 1 means
faster). Mean completed one-second depth fell from 7.1667 to 7.0833. Both required
five-percent efficiency gains failed. Initialisation was 17.09s for the parent
and 17.17s for the prototype. The controller and workers closed successfully.

No teacher review, matches, value fit, release or upload followed this failed
efficiency gate. The prepared quality wrapper remains unrun and must not run for
this candidate. Selected v1.55 and its existing weights remain unchanged. Do not
repeat the same precomputed-table change merely because the source looks cheaper.
