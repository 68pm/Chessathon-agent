# Label v1.56's remaining defensive and conversion errors

The completed short screen selected v1.56 through four direct comparison wins.
The nominal2400 and2600 pairs each yielded a draw and loss, showing that faster
search has not resolved king defence and conversion. Keep the selected package
fixed while inspecting four specific decisions from those games.

Compare the played move and the independently supported root alternative for:
2600 Black15 ...g4/...Kg7;2400 Black24 ...Be6/...Bf8;2400 Black26 ...Qxb2/...Bc5;
and2600 White53 Rc5/h5 from the drawn game. These are exposed development targets,
including a mate-allowing pawn grab. Root scores are not descendant value labels.

Use the exact v1.56 source and its per-ply buffers. Temporarily disable root-policy
preference only in the forced-branch diagnostic. Search each branch to eight plies,
bounded by2million nodes and5seconds. Follow only exact, history-compatible table
entries; preserve partial traces explicitly. Restore policy, board, accumulators
and history. Quiescence probes use the new buffer arguments and100k nodes/2seconds.

Retain at most48 actual student or legal teacher-PV descendants. Independently
evaluate each nonterminal board at80k/320k nodes with complete replay history,
at most19.2million new teacher nodes. Preserve mate, unstable, checked and terminal
cases; finite training eligibility uses the existing declared filters. No fit,
new upload or independent holdout claim follows from this diagnostic alone.

Preparation and source hashes are frozen before use. Keep metadata unchanged
while this collector runs; if browser access recovers, record site activation
separately before editing any hashed version metadata. The user has been asked
to reopen Codex because browser automation still cannot connect.

Run serially after the completed match controller and all owned workers close,
under the existing capacity, STOP, owned-process and daytime cutoff guards.
