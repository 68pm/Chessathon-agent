# Next learning step: independently checked student continuations

Prepared while pawn-bitboards-screen-01 owns the CPU. No extra teacher or student
search may start until that controller and its owned workers close. Handle any
qualified release and authorised upload first.

The completed depth trace established wrong relative values even when defensive
alternatives were searched separately. Retain these four exposed diagnostic roots:
the2400loss at White24, the2600loss at Black23, and the public round76 win at
Black33 and Black44. Their alternatives cover a defensive sacrifice, queen trade,
quiet rook move and a stronger alternative to a pawn capture. Keep their full
histories and original independently verified labels.

Before this unrun experiment was consumed, the new bitboards candidate lost both
2400 games. Add two independently supported alternatives from those completed
reviews: White35 Qd3 versus Bc4, and Black15 ...gxf3 versus ...f5. These test a
quiet defensive bishop move and interruption of the bishop/queen king attack.
Black13 ...f6 was also a serious mistake, but the two teacher budgets disagreed
on its preferred alternative; do not invent a stable policy target for it.
This gives six diagnostic roots and twelve forced branches in total.

Create a new bounded worker against the selected archive's verified source.
Search both the played and preferred move separately, starting at depth7 after
the forced root move (eight total plies), with at most2million nodes and5seconds
per branch. Clear search tables between branches. These are diagnostics; do not
change playing code, root policy weights or the released archive.

Trace only exact transposition entries matching board hash, full history context,
halfmove clock and sufficient remaining depth. The selected54/55 classical core
has no extension-credit or quiet-attacker salt: do not copy those from the older
v1.53 descendant tracer. Stop at terminal positions, missing/nonexact entries or
the quiescence boundary; never invent a principal-variation continuation. Preserve
incomplete flags, returned bounds, scores, nodes and exact played histories.

Record at most48 student intermediate/end positions plus24 endpoints from the
already recorded teacher lines (prefixes4/8). Deduplicate with history retained.
Run a bounded local quiescence probe only after storing the trace, so its table
writes cannot contaminate traversal. After the student worker exits, independently
label each nonterminal endpoint at80k/320k Stockfish nodes. At most72endpoints means
28.8million requested teacher nodes before cache reuse. Preserve mate and unstable
values, and filter check/repetition/near-fifty-move/endgame positions out of the
position-network training set using the existing explicit domain rules.

These are exposed development labels. Never copy a root reward or root score to
an imagined leaf, and do not count a repeated root as unseen validation. Compare
static and quiescence errors to identify missing evaluation signals before fitting.
Any fit must log per-epoch positive and negative correction-cohort errors and
retain trained checkpoints for diagnosis; signed-value-01 omitted those per-epoch
details, so its rejection cannot identify a failing cohort by itself.

Current dataset proportions are recorded facts: broad training has3732negative,
7007positive and1261near-zero corrections; targeted training has23/40/4;
validation has375/701/124. Their similar proportions do not prove that sampling
imbalance caused the failed fit. A balanced-loss change needs a new declared
experiment and validation, not an assumed cure. No new value model is selected.
