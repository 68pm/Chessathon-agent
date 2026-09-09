# Scalar evaluator: short comparison against v1.54

The scalar evaluator passed11correctness tests and96ABBA probes. Its fixed-work
aggregate CPU ratio was1.15108 and median1.15783, with identical moves, scores,
depths and nodes. Mean one-second depth changed7.0417 to7.0833. Both imports took
about18.9seconds. Independent review of all12clock roots found identical choices
and equal mean regret at both teacher budgets, with no increased major/mate-loss
counts. These findings justify a playing test; they do not establish strength.

Freeze the exact candidate, exact v1.54 incumbent and exact v1.53 archive. Verify
the source-only ZIP under strict read-only startup, then play one colour pair
against each archive and one pair each at nominal2400/2600, at120s+0.5s. Use the
existing C09/D28/D65 development openings, keeping their exposed status explicit.
Only a clean played2600win allows the conditional2800pair. Each pair has a1500s
bound; no stage starts unless it can finish before15:40BST.

Review every game through feedback_matches_windows while all playing files stay
frozen. Require at least1.5/2against v1.54, at least1/2against v1.53, no operational
failures and review of all rated evidence, plus all earlier gates, before release
selection. Ties retain v1.54. No extra games to chase a favourable result.

If the complete evidence justifies a successor, its next number is v1.55 and all
55previous ZIPs must remain byte-identical. Automatic Chessathon submission is
authorised, subject to observed validation and newest active version; currently
browser control fails before connection. GitHub publication is separate from
competition upload. No calibrated Elo or active submission is claimed by this
controller. Failed previous experiments and their evidence remain preserved.
