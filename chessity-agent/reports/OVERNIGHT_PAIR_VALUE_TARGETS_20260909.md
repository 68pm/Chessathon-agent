# Independent descendant targets from the D65 pair

The compiler-repaired v1.53 control scored 0W/1D/1L at nominal 2400. Both games
and their separate experimental policy checkpoints were fully audited. Across
134 agent moves the reviewer supported 85 good moves and penalized 11 mistakes.
The phase counts are five opening, 51 middlegame and 78 endgame moves.

The loss's first confident error was 23.e4 instead of Rf3. The draw also contains
missed chances to preserve an advantage: 30...Qg5 instead of Re2, 31...h5 instead
of Qd8, and 35...Rg1+ instead of Bd6. At the final one, the two budgets estimate
the preferred continuation at +164/+210cp and the check at -10/0cp. Earlier in
the draw, 25...g4 and 26...Bf4 both missed the quiet king move Kg7. These are
finite-search estimates and specific development targets, not proof of wins.

Prepare at most 40 descendants after two or four plies of independently supplied
best/played teacher continuations, including the two ending errors at moves
39 and 41. Exclude checks, terminal/repetition-sensitive positions, high draw
clocks, mirrors/duplicates and collisions with prior targeted value positions.
Reanalyse each endpoint itself at 80k and 320k nodes. Retain only finite scores
within 1500cp that agree within 100cp; preserve excluded mate/unstable results.

Both colours share the same D65 start and remain one held-out source group. The
targets are reserved from position-value fitting before endpoint labels exist.
The prior rule-value model and its failed results remain unchanged. Before any
future new fit uses this as a holdout, also remove collisions with its broad
training data. These selected error descendants are development diagnostics and
must never be presented as independent playing-strength evidence.

Run endpoint analysis only when other engines, games and feedback have closed.
The frozen maximum budget is 400k nodes per endpoint. No model fitting or release
selection is part of this preparation or labelling step.
