# Isolated king-pressure transfer into exactv1.56

The pawn-threat reduction guard regressed43Nxe5 and failed. It is excluded.
Currentv1.56 tapers all king-ring pressure with material phase, although a queen
and a second attacker can remain dangerous after exchanges. A coordinated attack
term helped the earlierv1.52 tactical pilot, but that release contained slower
search and several other changes. Test only the already specified king-pressure
term on exactv1.56: collect pressure units in the existing mobility loop (minor2,
rook3, queen5 per attacked king-ring square); with our queen and at least two
attacking pieces add min(250,2*units^2), symmetrically for the opponent. No extra
board scan, older search extensions, queen/passed-pawn correction or new weights.

Check exact difference against independent python-chess attack sets, both colours,
queenless/lone-queen cases, cap and board preservation. Search/terminal/history
functions must be unchanged by AST comparison. Test the same12 declared evening
development roots in1second ABBA order. Use80k/320k teacher budgets and deeper
2.56M/10.24M for23...Re6; require no new major/mate regression, non-increasing
mean regret at both budgets and at least10% reduction at one budget. This is a
new integration into the current engine, not a replay of oldv1.52 strength tests.

Only a passing candidate gets the reserved B12/D48 four-game comparison versus
exactv1.56, requiring>=3/4, then the predeclared short2400/2600 pairs and read-only
checks. Match openings remain unplayed and untrained as of this declaration.
No version number or selected ZIP changes on failure. Every played game reviewed.
