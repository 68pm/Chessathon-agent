# Cycle 14: diagnose quiet defence and promotion protection

The v1.48 pair and its127-move audit are complete. Keep v1.41 selected. Before
another fit or engine change, reconstruct two measured failures from actual
history:23.Ne1 versus Ne5 and56...Bxe8 versus...Rb7. Run one full-window trace
per root at depths1â€“6 on frozen v1.48, with each search limited to2 seconds and
one million nodes. Record root decisions and both forced-child values, retaining
incomplete searches. No repeated match pair or unchanged speed experiment.

Use the traces to distinguish position evaluation from tactical horizon effects.
Choose any subsequent code/learning experiment only after this diagnosis. The
existing two teacher budgets and these complete histories supply targeted data;
no new broad data, extra epochs or long independent consistency check is needed.

Both traces completed. Ne1 remains preferred through depth6 (-78cp versus
Ne5 -118cp), while the teacher rates Ne1 around-355cp and Ne5 around-24cp.
For the endgame, Rb7 is chosen at depths1â€“2; Bd5 at3â€“4; Bxe8 at5â€“6. The engine
sees g8=Q after Bxe8 but still values the resulting queen-versus-rook/bishop
position at about+364cp, whereas both teacher budgets return0. Thus simply
searching deeper does not fix this evaluated continuation. This is a concrete
leaf-judgement gap, distinct from the earlier Rc1 horizon issue.

Next test one material-context correction: advanced passed pawns should receive
less endgame credit when facing a queen without a queen of their own. Keep its
scope and coefficients fixed before measurement; verify both colour perspectives
and broader known-error roots. No new neural fit is justified until a useful
signal is demonstrated. The targeted signal, if useful, can become an explicit
feature or auxiliary target for the existing residual architecture.
