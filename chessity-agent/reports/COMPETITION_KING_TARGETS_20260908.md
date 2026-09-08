# Queenless king activity trial from the real drawn game

Both archived41 and selected53 allow threefold at80.Ra1 in round68, where an
independent full-history teacher retains+209/+204cp through Rf1/Re1 and king
activity. The root scout integration failed its quality gate (four to five
paired major errors, no100cp repair) and is excluded from this new prototype.

Change ONLYclassical evaluation in selected53: in queenless positions with
material phase<=8, reward proximity of each king to the closest enemy pawn
without pawn support. The fixed16cp per Chebyshev distance step is added to the
endgame score and tapered normally. No target means distance7. The term is
symmetric and bounded112cp before tapering. No square-specific rules, draw
contempt, search/timing/policy/weight changes or resumption of stopped cycle38.

Independent python-chess attack-set oracle checks all nine PGNs, color mirrors,
restored board, no-queen/phase activation and bare-king neutrality. Verify every
other core AST unchanged. No recursive-JIT test duplicate before the worker.
Then use the same14roots/one-second limits/90s init/360s worker/actual histories
as the recent53 baseline. Review changed choices80k/320k, up to5.6M new requested
nodes. Passing requires the prior trial's strict lower mean regret and fewer
paired200cp errors, no new major/mate error, one100cp repair AND draw-root regret
<=50cp at BOTH budgets. Exposed development data, no Elo inference or auto release.

Serial CPU, hidden SystemPowerShellNormalPriority4 from launch,2048MiB free disk
and768MiB free physical RAM before every heavy process,20minute capacity wait,
new STOP flags interrupt. Retain every failed trial and all existing releases.
The deleted overnight automation remains deleted. Exported root labels match
the768-input network format, but no neural fitting is claimed; descendant
supervision still requires independently labeled descendant positions.
