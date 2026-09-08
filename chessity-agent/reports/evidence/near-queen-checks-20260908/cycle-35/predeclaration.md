# Cycle 35: bounded quiet checks after a queen approaches the king

Predeclared 8 September 2026 before measurements. Selected v1.52 stays frozen.

Cycles33/34 verified a missed mate in six after greedy rook captures, mixing
checking captures with four quiet checks. The original two normal-search check
extension credits have already been spent. This new mechanism is distinct from
the rejected cycle21 one-layer quiet-check pilot and does not include cycle31 PVS.

Change only search and a geometric helper. At a quiet quiescence node with
qdepth<=4, a queen within Chebyshev distance2 of the opposing king activates
one attacking side for the rest of that line. That side may search at most four
quiet checks, interleaved with ordinary captures and complete check evasions.
The existing qdepth12/ply96 limits remain. Quiet nonchecks are discarded after
legal make/unmake; every checked defender retains all legal evasions. TT context
includes remaining quiet-check credits and the attacking side, as well as the
existing extension credits. All evaluations, weights, policy, clocks and root
selection are unchanged. Explicit zero quiet credits provide a control mode.

One frozen pilot:

1. A production prototype worker initializes within90s. Verify queen-near-king
   geometry against python-chess on240 deterministic positions for both colors;
   board/state unchanged. At zero quiet credits, all five cycle32 depth6 forced
   scores must match unchanged52 within the same500k-node/8s limits.
2. On BOTH cycle34 mate-in-six positions after dxc5/Qxc5, full-window depth0
   quiescence with four quiet credits must find a positive mate score within
   500k nodes/8s; no forced move or teacher search inside the student. With zero
   quiet credits retain the measured scores separately. Check mate/stalemate
   priority at halfmove100, and a512-node interrupt restoring pieces, history
   and accumulator. Incomplete scores are null and fail correctness.
3. Only if correctness passes, the same worker measures all21 exposed roots once
   at1second, fresh TT/history, policy disabled. A separate unchanged52 worker
   does the same21 probes. All moves legal, wall<=1.25s, initialization<=90s.
4. Cheap gate: fewer repeats of the original played mistakes and the recent
   Bxf2+ choice changes. Only then review all42 choices at80k/320k, reusing the
   compatible cache, at most16.8M new teacher nodes. Require strictly lower mean
   regret at BOTH budgets, no new stable paired200cp error/mate loss, and the
   recent Bxf2+ root choice within50cp of the verified best at both budgets.

Passing permits a subsequent read-only check and exactly two predeclared
120+0.5 games versus52, not automatic release or an Elo claim. Failed correctness
or quality leaves52 selected; no unchanged retries or threshold relaxation.

Engine code first: continue forcing lines without unbounded check extensions.
Learning second: retain mate/counterfactual labels distinctly; do not fit only
the favorable imagined leaf. The exchange-ending value error remains separate.
Targeted data third: use the two verified mating positions and all21 prior roots.
No game download or blind fitting is needed for this implementation.

Serial local CPU, hidden Windows System PowerShell Normal priority4 from launch.
Both2048MiB disk and768MiB physical RAM before every heavy process; capacity waits
at most20minutes, both STOP flags honored. Each worker tree at most360seconds.
Freeze all sources/histories/cache seed/candidate bytes before measurements and
preserve every outcome. No games, neural update or new package in this pilot.
