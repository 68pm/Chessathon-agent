# Bitset attack trial: faster fixed work, failed combined gate

The corrected bitsets-02candidate passed18compiled correctness checks, including
30,720attack queries,6,659legal-child states/hashes, special moves, reversible
metadata and known perft counts. bitsets-01is preserved separately: an LLVM flag
construction error caused15test failures and no search measurements.

All176balanced probes completed on22exposed development roots. At250knodes,
score/depth/move/node counts matched exactly. CPU totals were90.390625s for53and
75.75s for the prototype:1.19328aggregate speedup,1.07800median per-root ratio.
Startup was76.1843s and71.7940s respectively, both below90s.

Under1second clocks, mean completed depth fell from4.45455to4.36364. The declared
gate required both useful speed and nondecreasing mean clock depth, so the trial
failed. Timing varied substantially between repeated probes; this does not justify
changing the criterion or rerunning the unchanged pair until it passes.

No clock-choice teacher review, full game, new release or Elo claim followed.
v1.53remains selected. The prototype ZIP is preserved only as experimental evidence:
SHA25648253f69c1a8e98fbdab437bd1f2b35c574252c0cd184f02aa24ff5907347a7a.
Sources, all measurements and the decision are frozen in
runs/overnight-20260909/bitsets-02; the completed scheduled task was removed after
verifying its owned workers had exited.
