# Improvement cycle 01 — compiled calculation

The original compiled-search-v2 candidate scored **8W/0D/0L against preserved v1.14**
in the fixed development match at120+0.5. The nominal2400 screen scored1W/1D/2L;
the2600 screen scored0W/1D/3L. All16 games finished and passed referee audits.
The target is not reached. v1.14 remains the official upload pending independent confirmation.

The baseline audit screened541 own moves from12 previous games. It found18 >=200cp
errors stable at80k/320k teacher budgets, plus4 choices that allowed a teacher-found
forced mate at both budgets. These mate lines are finite search findings, not exhaustive
proofs. Several early errors occurred with more than60s remaining.

The compiled move generator passed known perft counts,1800 random differential legality
and exact classical-evaluation comparisons, special-move/hash checks and fixed-depth
search score comparisons. Source is original, using the permitted Numba0.67 runtime;
no third-party engine code or native executable is shipped. The v2 package passed strict
read-only/no-socket/no-subprocess inference. Windows platform detection is handled by
read-only OS information; the audit was not relaxed.

On18 previously audited mistakes with equal1s diagnostic budgets and root policy disabled,
v1.14 repeated12 original errors and matched the teacher's top move0 times. Compiled v2
repeated6 and matched5. Alternative good moves are not counted by this top-one metric.
Compiled v2 visited5.31M nodes over18.03s versus177k over18.01s for v1.14. These are
shared-host development timings; final isolated confirmation remains necessary.

The first original768-32-1 residual value network trained on30,000 existing CC0 positions
plus74 eligible verified own-position corrections, with4,000 original-ECO-split validation
positions. Its retained epoch7 reduced capped validation MSE from91,758 to73,952cp^2.
The network is used at every search leaf. Its diagnostic searched3.84M nodes, repeated5
original errors and matched3 teacher top choices. The mixed results and evaluation cost
require matched games; no neural strength claim is made. Those games are running as cycle02.

Elementary endgame data was obtained from the python-chess maintainer's public Syzygy
fixtures, with Git blob/SHA256 verification:10 table files plus source attribution,
26,558 bytes. All40 sampled KQK/KRK wins converted against tablebase defence. This is
permitted runtime endgame data, not a claimed neural training result or a rated victory.
23 balanced starting FENs from held-out ECO groups have been verified independently
of candidate outcomes for future confirmation.

The next efficiency experiment updates two hidden accumulators on moves instead of
rebuilding the network input sum at every leaf. Weights stay identical. Its special-move,
restoration and numerical parity tests passed. It recovered about5% node throughput
on the same18 positions, with unchanged teacher agreement and repeated-error counts.

A more useful measured optimization stops terminal legality checks at the first legal
reply. At exactly50,000 nodes per position, all18 completed-depth/move/score results
matched the frozen compiled control, while total search time fell from4.312s to2.563s
on the shared host. Fifteen compiled-core tests passed, including mate, stalemate,
special moves and1800 random legality comparisons. This is a throughput result,
not a match-strength claim; independent confirmation will use the changed runtime.

Cycle02's learned network comparison finished2W4D2L against the same compiled search
without the residual. The eight-game test provides no clear improvement from learning.
Its2400/2600 screen continues. The next confirmation therefore keeps the classical
evaluation and combines the verified search-efficiency change with elementary tables.
The learned weights remain preserved for later targeted experiments.

Evidence remains under runs/improvement-loop-20260907. Frozen candidates remain immutable.
