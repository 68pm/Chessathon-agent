# Consistency study interrupted before a completed game

The first two games stopped after the last recorded moves at16:49:59 UTC on
7 September2026. On inspection, both controller processes and all Stockfish
children were absent, while the saved status still said running. There was no
captured error. The cause of the external process termination is unknown.

**Zero games completed.** No win, draw or loss is assigned to either unfinished
game. Both registered consistency attempts are marked interrupted and invalid;
neither opponent qualifies for replacement. The original protocol, preparation,
source, logs and unfinished snapshots are preserved. This is not successful
independent consistency evidence and no engine strength is inferred from it.

The selected upload is still v1.41. Its earlier completed independent tests were
23W/1D/0L versus v1.14,3W/4D/1L versus nominal2400 and0W/3D/5L versus nominal2600
at120+0.5. Those are separate from this interrupted attempt.

A one-time Windows Task Scheduler launch probe succeeded and was removed. A
service-owned launcher is available for future long jobs. The user has been
offered a choice between the full consistency run and prioritising smaller
diagnostic tests followed by improvements. Full consistency tests freeze the
agent; they measure reliability and do not train it.
