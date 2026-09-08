# Root scout integration after the new competition review

The user requested persistent old/new problems and fixes. Exact v1.53 reduces
paired 200cp errors from seven to four on the thirteen finite development roots,
but both versions choose a forced-mate losing move in a fourteenth root. The
current quiet-check search completes depth1 there versus v1.41 depth5. This is a
new observed cost of the v1.53 search and justifies a bounded efficiency trial.

Integrate only the root scout/re-search algorithm from the earlier v1.52 cycle31
prototype into v1.53. Every other function and constant must be AST-identical.
Cycle31's old quality gate remains failed; this is a changed base and newly
downloaded game set, with no reuse or reinterpretation of that failed result.
No new weights, draw contempt, opening rules, timing changes or cycle38 restart.

Run the independent root-window oracle tests (signed bonuses, mate bands,
fail-hard scouts, interruption restoration and unchanged source). Then one fresh
worker,90s initialization, fourteen one-second probes with policy disabled,
actual game histories and fresh tables, matching the saved v1.53 review.
The saved baseline is a recent measurement, not a randomized repeat; keep this
limitation. One360s worker cap. Failures are retained, no unchanged retry.

Evaluate changed choices at the same80k/320k budgets, reusing exact already
reviewed moves. Maximum5.6M new requested teacher nodes. Gate: at least thirteen
common finite roots; lower mean regret at BOTH budgets, strictly fewer paired
200cp errors, one repair of at least100cp at BOTH, no new paired200cp or mate
loss. Report the draw position separately whether improved or unchanged. Passing
is only a development gate, never an Elo or guaranteed competition improvement.
No automatic release from this script.

Serial hidden SystemPowerShell NormalPriority4 from launch. Check2048MiB disk and
768MiB available physical RAM before every heavy process,20minute maximum wait.
New STOP flags interrupt. Deleted overnight automation remains deleted. Preserve
all released agents, frozen review sources, interrupted work and failed trials.

Engine efficiency is first priority here. The verified positions and opponent
refutations become tactical/descendant training targets, not duplicate root
labels on arbitrary leaves. No neural fit is claimed from replaying positions.
