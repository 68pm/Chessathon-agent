# Pawn-extrema short playing screen — 9 September 2026

The isolated v1.42 passed-pawn optimisation passed exact evaluation and fixed-node
parity, with aggregate CPU speedup1.05605 and median1.05806 over20roots. Independent
80k/320k teacher review of clock choices found identical mean regret and no new
major mistakes or mate losses. This justifies a small playing screen, not a rating.

Freeze the exact candidate and both archived controls. Validate the packaged
source under strict read-only operation and the90second initialisation budget.
Then play one colour pair each against exactv1.42 (C09), exactv1.53 (D28), nominal
Stockfish2400 and2600 (D65), all120seconds+0.5seconds. Eight games total, plus one
conditional2800pair only if the2600pair includes a clean played win. Stop on
operational failures. Each pair has a1500second hard bound; no stage starts unless
it can complete before15:40BST. Do not add games to obtain a favourable result.

Review each win, draw and loss through feedback_matches_windows, retaining its
history-aware independent Stockfish move labels and experimental policy checkpoint.
The candidate's playing files stay frozen; these fits never change the live match.
The exposed C09/D28 roots make this a development comparison, not independent Elo
validation. No claim of a stable rating follows from these eight games.

Promotion requires no operational failures, >=1.5/2vs42 and >=1/2vs53, plus the
passed tactical/efficiency/read-only gates and review of all rated evidence. Tied
results keep42. A successful screen authorises review and packaging; it does not
itself change aliases or submit to the website. The user has separately explicitly
authorised automatic upload of a demonstrated stronger successor. Verify website
validation and newest active submission before claiming that it is in use.
