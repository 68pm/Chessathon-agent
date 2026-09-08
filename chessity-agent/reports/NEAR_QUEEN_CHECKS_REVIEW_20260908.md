# Bounded review of the cycle35 comparison

Before selecting a release, review every candidate move in the two predeclared
120+0.5 games against v1.52. At this declaration the White game has ended in a
checkmate loss and the Black game is still pending. Keep both outcomes and the
original practical qualification rule, regardless of the second result.

Launch only after both games, the practical controller and all its owned
processes finish. Replay and audit both clocks, moves, sources and outcomes.
Use the existing20k-node best/played screening and80k/320k verification only for
suspicious choices. Maximum requested work is840,000 nodes per candidate move;
freeze the actual move count and source hashes before the first teacher call.
Reuse identical best/played choices. Check both2048MiB disk and768MiB memory
immediately before teacher launch, honor STOP flags before every analysis,
and run hidden at Normal priority. No new games, candidate initialization,
network fitting or altered playing code is part of this review.

Record every reviewed move with its actual history and both teacher budgets.
Separate the first warning or losing transition from the terminal game phase;
retain squandered advantages and mistakes in wins and draws as well. Phase
analysis reuses these labels and requests zero new teacher nodes. The legacy
old-baseline source identifier in the shared audit is a generic prefix: actual
candidate paths, source hashes and histories identify this build.

Engine search and evaluation remain first priority: determine whether these
games expose another missed continuation or a misvalued exchange/endgame.
Useful learning is second: any later targets must include stronger opponent
continuations and independently verified descendant values within a compatible
network objective. These two games and existing tactical cases provide the
targeted data. This review does not itself train the model or establish Elo.
