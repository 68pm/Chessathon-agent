# Four games after canonical startup recovery

Declared before any results from this candidate's first ordinary games.
The startup-complete/plain-diagnostics candidate has the same playing search,
evaluation, clocks, policy weights and tables as selected v1.41. Its changes
are confined to startup readiness and the compiler's diagnostic presentation.
Strict read-only checks and one canonical runner request passed; the instrumented
request's native crash remains preserved and prevents a universal reliability claim.

Play exactly four serial games at120+0.5: one colour pair each against nominal
2800 and3000, using the same preselected C58 start in
configs/overnight-baseline-openings.json. This candidate has not played these
games before. The earlier v1.41 attempts had zero moves and remain a separate
failed operational baseline; their results are not replaced. Play all four
regardless of chess outcomes and do not extend the batch to obtain a win.

Candidate: candidates/compiled-startup-plain-v1. ZIP SHA256:
`f23376c7c33ad28ccb2276c16b8b242c84e34492e7ef3910691e4cb9b58a79e2`.
Use the unchanged serial runner and its independent legal/clock/source/outcome
audit. Before launching, require both capacity guards and canonical protocol
success. No teacher analysis, training or JIT experiments during the games.
After all four, run the existing own-move audit, then review first deterioration
and missed conversion opportunities by phase. Do not infer a chess weakness from
an initialization failure or treat a flag as proof of superior playing strength.

A practical recommendation may treat this as a startup reliability revision only
if all four games have valid audits and no candidate initialization, crash,
illegal-move or flag failures. Its playing logic must still match v1.41 outside
the documented startup changes. Chess wins are reported, but no promotion as a
stronger trained/search model or higher Elo follows automatically from this batch.
If the operational criterion fails, retain v1.41 and diagnose the recorded failure.

Engine need: establish ordinary play after the readiness repair, then return to
the pending useful-depth hypothesis. Learning need: preserve weights and use the
completed capacity review before any further fit. Data need: new legal games may
finally provide current-build errors against these settings; use those first,
without an indiscriminate download or long consistency study.
