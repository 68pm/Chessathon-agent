# Cycle30: trace all four new first warnings before changing the engine

The frozenv1.52 rated screen produced0W1D1L at2400 and0W0D2L at2600, without
runtime failures. Its173-move audit located the first warning in each game,
including the draw's missed advantage. Diagnose all four of these positions;
do not select only a favorable example or replay the completed match screen.

Use unchangedv1.52 in one new worker. Reconstruct each position's actual history
and compare its played move with every distinct80k/320k best alternative. There
are nine root choices total because the2400 loss has two different teacher queen
alternatives. Search each choice with a full window at depths4,6,8, clearing TT,
killers and history before each branch. Root policy is disabled for this diagnostic.
Use at most500000 student nodes and8seconds per branch,27branches/13.5million
nodes maximum. Import/warmup<=90seconds precedes finite search timing. A360second
parent bound terminates only the worker's owned Windows process tree.

Record complete scores separately from incomplete branches; a cutoff is not a
zero evaluation. Assert legal root choices, exact FEN/history, restored board,
hash history and accumulator, unchanged candidate/source hashes, and wall time
<=8.25seconds per branch. Respect STOP flags, hidden Normal priority and both
2048MiB disk/768MiB RAM guards with a20minute maximum capacity wait. No overlap
with games, teacher analysis, fitting or another JIT worker.

This is diagnosis only: zero teacher nodes, fitting, games, new engine changes
or selection claims. Compare completed preferences with the existing verified
alternatives to distinguish depth sensitivity from persistent value error. The
teacher lines are finite estimates; root scores are not labels for every child.

Engine calculation and value correctness are first. Useful learning comes second:
if deeper search still misses the stronger opponent continuation, identify the
specific descendant and compatible target before fitting. Targeted data are
these four already verified first-warning positions with full game provenance;
no new broad game collection is needed. Use the findings to predeclare one new
engine or learning hypothesis, preservingv1.52 and all failed prior experiments.
