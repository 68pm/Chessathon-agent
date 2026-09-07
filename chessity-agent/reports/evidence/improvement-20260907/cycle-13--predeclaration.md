# Cycle 13: prove one legal pawn move before generating all moves

Base: frozen v1.41 alone. At every quiet quiescence node, its stalemate guard
generates the entire pseudo-legal list before testing the first legal move.
For a side already known not to be in check, a one-square pawn push is legal
when its destination is empty and the source shares neither rank, file nor
diagonal with its own king. Removing that pawn cannot uncover a sliding check;
the move does not change a knight or pawn attack on the stationary king.

Use this sufficient geometric proof as an early return in has_legal_move.
Otherwise use the exact existing generator and make/unmake test. No assumptions
about en passant or castling; they stay on the fallback path. No evaluation,
weights, ordering, pruning or earlier failed prototype code is included.

Validate against python-chess legal-move existence on1500 random legal boards,
pins, checks, mate, stalemate, promotion and en passant cases, with state parity.
Use the same11-root250k-node gate and two alternating passes: exact completed
depths, nodes, scores and moves, at least10% aggregate speedup. Stop on failure.
If passed, check package/read-only operation and a two-game colour pair versus41
at120+0.5. These are short development checks, never Elo certification or a long
independent consistency study. Keep41 until practical replacement evidence.

Engine work first. No new learning fit until calculation costs are resolved;
existing diagnosed positions supply the targeted data for this iteration.
