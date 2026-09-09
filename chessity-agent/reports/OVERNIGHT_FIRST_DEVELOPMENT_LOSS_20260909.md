# First actual-clock development loss

The compiler-repaired v1.53 control lost as White to nominal Stockfish 2400 in
the D65 start. It was checkmated after 107 plies. This is a separate build from
the selected v1.53 ZIP; neither side had a recorded operational failure.

The resumed Stockfish review covered all 53 agent moves: two opening, 25
middlegame and 26 endgame moves. It identified 22 supported good moves and two
confident mistakes; 20 moves remained uncertain at the two analysis budgets.
The separate policy update must not be presented as proven strength improvement.

The first confident error is **23.e4**. Both 80k and 320k-node reviews prefer
**23.Rf3**, evaluating that continuation at -56 and -50cp and the played move at
-237 and -252cp. Investigate the quiet rook alternative and the central exchange
continuation at the game's actual search budget. The magnitude is about two
pawns of estimated disadvantage, with the usual finite-search uncertainty.

**33.Qxf4** loses another estimated 234/212cp, but even the preferred continuations
already evaluate at -739/-796cp. Its best alternative differs between budgets,
so the review correctly leaves its corrective policy target unset. This late
capture is a secondary target; fixing it alone would not explain the original
collapse. The terminal ending was already a forced loss in the later reviews.

The complete history and both labelled root continuations are frozen in
development-root-01/targets.json. Their action rewards are provenance, not
descendant value labels. Any suitable quiet descendant requires its own teacher
analysis before position-value learning. Keep this D65 pair in one source group.
