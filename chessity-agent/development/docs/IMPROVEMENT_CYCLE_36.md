# Cycle36: defensive continuations and descendant values

The completed v1.53 screen lost three games without operational failures. Diagnose
their first stable losing transitions:10...Nc6 versus Kh7,14.Qb3 versus h3, and
19...Bh4 versus Be6. These are new positions, not retries of old failed gates.
The draw and earlier15...Na3 warning remain preserved in the full rated report.

Use unchanged released v1.53, policy off, real histories. One fresh worker searches
each of the six forced choices once at full-window depth6,500k nodes/8 seconds,
fresh TT/history/killers. Incomplete scores stay null; no larger-budget retry.
Trace only exact TT entries with valid depth, halfmove clock and extension context.
This core also requires the quiet-check context salt (initial attacker0/credits4,
encoded10). Stop explicitly at quiescence, terminal state or missing/nonexact entry.
No claim of a full continuation from a partial trace. Keep remaining extensions.

Combine student endpoints with prefixes4 and8 from both budgets' best/played
teacher lines. Deduplicate actual histories, at most30 endpoints. Independently
probe each nonterminal endpoint with100k-node/2-second quiescence, then, only after
the student exits, review it at80k/320k teacher nodes. Maximum student6million
nodes and teacher12million requested nodes; initialization<=90seconds, each owned
worker tree<=360seconds. No games, fitting, model changes or root-label reuse as
endpoint labels. Quiescence probes are local diagnostics, not invented PV moves.

Verify legal moves and restored pieces/state/accumulator/hash history after every
probe, all source hashes and candidate identity. Record material, king pressure,
passers, pawn cover on the king's file and absolute pins as descriptive features.
These do not by themselves prove causality or justify a square-specific patch.
The aim is to distinguish missed defensive continuations from misvalued positions.

Engine diagnosis comes first. Useful learning comes second: assess independently
verified counterfactual values against the network's representable correction
range before a new objective or fit. The three actual losses supply targeted data.
All examples are exposed development data. No broad download or repeated epochs.

Use serial hidden Normal-priority execution, STOP flags, and2048MiB free disk plus
768MiB RAM before every heavy process; capacity waits<=20minutes. Preserve all
incomplete probes and failures. Keep the released v1.53 ZIP unchanged.
