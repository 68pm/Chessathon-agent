# Probe current code before correcting public losses

The public PGNs identify the team, but not the submitted source hash. A new
engineering patch should first establish which earlier mistakes the current
selected release still makes.

After fast-legal-screen-01 and release handling finish, freeze the then-selected
ZIP and source manifest. Use five exposed public turning points with full history:
our round 78 moves 10, 11 and 13 (Bxh7+ opportunities and exf6 versus Ng5), our
round 77 move 18 (...Be6 versus ...Kg7), and the leader's drawn round 78 move 130
(...g5 versus ...Kg7). Each has a stable alternative in the existing two-budget
review. This is preparation for tactical and defensive changes, not an Elo test.

Run exactly two cold-table searches per root, at one and three seconds with a
five-million-node cap. Retain the selected agent's root policy, reductions,
evaluation and move-ordering settings. Observe completed iterative-deepening
choices without changing the compiled search. Keep unfinished iterations and mate
scores distinct from finite evaluations. Verify unchanged board and move history.

Close the student worker before using the existing history-aware Stockfish teacher
to review each distinct selected move, the originally played move, and the earlier
verified alternative at 80k and 320k nodes. Reuse matching cache entries. Do not
force agreement with the earlier labels if a fresh estimate differs, and do not
map root action rewards onto unlabelled descendant positions.

Diagnose the earliest persistent mistakes before making a bounded behavioural
change. Do not fit a network, number a release, or modify the upload from this
probe alone. Keep capacity and STOP guards, a bounded supervisor, serial heavy
work and the current daytime cutoff. Never run concurrently with the match screen.
