# Recover useful alternatives without inventing a unique best move

In the new nominal2400 played loss,33.Bxc4 lost237/272cp from an approximately
equal position. The original reviewer confidently penalised it but left its
policy target empty because the two best-move searches proposed different
alternatives. The fixed curriculum correctly declined to invent one target,
but consequently omitted this key recoverable error from its descendant queue.

Independently analyse both proposed alternatives and the actual capture as
restricted root moves at80k and320k nodes. Keep every score and uncertainty.
An alternative qualifies only when both estimates are finite, agree within100cp,
are within50cp of the best available measured reference at each budget, and
improve on the played move by at least70cp at both budgets. Multiple alternatives
may qualify; do not rewrite the original review or force a unique best move.

Apply the same process to the exposed D65 Black35 counterfactual Qxd4 versus
Qd6. This specifically labels the inferior capture line which was absent from
the earlier actual-game Rg1+ descendant set. Replay exact histories and verify
all moves. Independently label quiet2/4/6-ply descendants of the played move and
verified alternatives, excluding prior/model/queued duplicates and unsuitable
check, terminal, repetition or draw-clock positions. At most8M teacher nodes.

Keep the existing D65 validation/development attribution. This operation does
not fit a network, change policy rewards, promote a candidate or establish Elo.
Any later recipe reusing these already exposed positions for training requires
a new disjoint source-group value check and honest development attribution.
Run only after the current engine trial exits, with capacity/STOP/deadline checks.
