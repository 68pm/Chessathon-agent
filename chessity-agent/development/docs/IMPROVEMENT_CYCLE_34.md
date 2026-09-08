# Cycle 34: resolve the continuation after the correct Kh1 defense

Predeclared 8 September 2026 before measurements. Cycle33 has completed.
It corrects the previous hypothesis: Kh1 IS the strongest teacher defense after
Qe3+, +544cp for White at both budgets. Kh2 is also winning; Rf2 loses by mate.
The error lies later: the student expects a winning c5 rook capture for Black.

One teacher-only diagnostic examines four exact-history positions from those
recorded continuations: after Kh1; after Kh1 dxc5; after Kh1 Qxc5; and after
Kh1 Qxc5 Qxf7+ Kh8 Qf6+. At each, analyze the unrestricted best move at80k/320k.
Also analyze the student's dxc5/Qxc5 choices at the first position, Qe7 at the
second, and Qxf7+ at the third, unless already equal to the best move. Maximum
3.2 million requested nodes. Preserve finite/mate scores and all PVs, reporting
White perspective consistently. No student JIT, root retest, game or fit.

Engine first: determine the tactical continuation before implementing a general
search fix. Learning second: use actual counterfactual descendant labels, not
the misleading favorable leaf. Targeted data third: only these four diagnosed
positions are needed. This is not an Elo or promotion gate.

Freeze histories and source before analysis. One hidden Normal-priority4 Windows
System PowerShell task; both2048MiB disk and768MiB RAM required before each
process and Stockfish, capacity waits<=20minutes, STOP flags honored. Owned
worker tree bounded360seconds. Preserve all outcomes and v1.52 unchanged.
