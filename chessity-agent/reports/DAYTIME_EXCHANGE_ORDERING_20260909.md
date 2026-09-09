# Bounded exchange ordering — 9 September

The isolated hash change had no measured CPU benefit and is not integrated.
Use exact v1.42 as this candidate's parent. Change move ordering only; preserve
evaluation, model weights, hashes, search windows, legal moves and clock policy.

The prior exchange experiment generated whole capture lists recursively up to
16 recaptures. Instead inspect attackers of one square using pawn/knight/king
offsets and eight sliding rays, with legal king/pin checks. Bound continuation
to six recaptures. If more are needed, mark it uncertain and keep original priority.
Use this only at root and the immediate opponent reply, at depth at least three,
and only when a more valuable piece captures a cheaper one. Preserve original
priority for checks, check evasions, promotions, en-passant and transposition hints.
Demote a losing capture below quiet moves; never delete it, reduce it as a quiet
move or prune it from quiescence. Nonchecking sacrifices remain searchable.

Check direct versus independent legal-recapture oracles for small positions,
x-rays, pinned defenders, illegal king recaptures and exact state restoration.
Clock probes use 12 existing development roots plus one preselected mistake from
each of the four recent v1.42 C09/D28 games. Use serial warm ABBA probes at one
second, recording every result and failure. Teacher labels at 80k/320k nodes
must show no new major mistake or mate loss and no worse mean regret; require
at least one improvement of 100cp at both budgets before spending games.

Passing this gate permits strict upload validation and the saved eight-game
screen, not immediate promotion. Every game must be reviewed. Values and future
training data remain independent of move rewards. Existing v1.42 stays selected
until the concrete short comparison supports a replacement.
