# Measure bounded defence with the diagnosed compiler repair

Declared before this combined candidate. Pure coalesced-search-01passed its
efficiency gate: one search variant,62.373s startup versus81.199s/three variants,
exact fixed-work parity,CPU ratio.9908and mean clock depth4.2273versus4.1818.
It then FAILED clock-choice quality: shallow mean regret126.068->128.727cp,
deep149.568->146.091cp, with increased paired-major counts at round72move9and
field Istanbul move34. Preserve the failure; no full games or release followed.

The earlier queen-defence-01had passed its compiled rule/control tests but never
reached position probes because startup exceeded90s. This fresh candidate combines
that unchanged bounded legal-safe-queen-check defence with the measured compiler
repair so the defence can be tested. The compiler change preserves fixed-work
decisions; it is not being promoted as stronger on its own. Do not retry either
old run or hide their failed gates.

Apply the full explicit root boundary, including all three defaults (quiet checks4,
attacker0, defensive credit1), and widen the three recursive qdepth zeros. Everything
else is identical to the frozen queen-defence implementation. Normalize all casts
and explicit defaults to prove AST identity to that variant. Reuse its15passed
compiled tests and preserve/hash their XML and source; new root-policy/abort and
integration tests verify the added boundary. Record actual engine variant counts.

The defence rule and quality gate stay as originally declared: one full legal
defensive ply at a nonchecked qdepth<=2horizon when a bounded legal safe queen-check
probe triggers; one credit per line in TT context. On the same22development roots,
run prototype/baseline90s starts and88ABBA1s choices. After both workers close,
review independently at80k/320k. Require>=100cp repair at both budgets somewhere,
nonincreasing mean regret at both, no additional paired200cp or mate-loss errors,
and legal/restored/on-time choices. No clock-depth prerequisite for this behaviour
change, no tuning of thresholds after measurement and no unchanged retry.

Keep all weights fixed, including rejected value fits. Opening/endgame regressions
in that fit require separate learning work, not automatic weight mixing. No broad
new data is needed for this targeted defence hypothesis. A quality pass permits
strict read-only validation and four reviewed short games versus53 before release
consideration; thereafter nominal ascent follows only actual clean wins.
