# Short practical screen of faster legal-move existence

Run the frozen fast-legal-01 prototype only after its correctness, efficiency and
clock-choice quality gates complete. The speed gate passed all 96 probes with
fixed-work parity and aggregate CPU ratio 1.15071. Its two changed timed decisions
reduced teacher regret; cached independent 80k/320k labels were reused, with no
new major-error or mate-loss regression. They remain development measurements.

Validate the exact candidate ZIP in the strict read-only harness first. Then run
one pair at the established 120s + 0.5s clock against each exact v1.55, exact v1.53,
nominal 2400 and nominal 2600. Both colours are required. Use the same declared
development openings and offsets as the prior screen. Only a clean played 2600
win and at least one point in that pair permit a further 2800 pair.

The unchanged preliminary selection gate requires at least 1.5/2 against v1.55,
at least 1/2 against v1.53, and no operational failures anywhere. Review both rated
pairs and every additional game through the Windows feedback wrapper. Losing a
nominal match is still useful diagnostic evidence. Inspect the complete results
before promoting; a higher version number or speed-only improvement is insufficient.

Keep playing weights frozen throughout. Post-game reward-policy fits remain
experimental. No calibrated Elo or reliable strength difference can be inferred
from this small screen. Keep the selected v1.55 ZIP intact until a successor is
qualified, packaged and selected separately. The user's automatic Chessathon
upload permission applies to a qualified stronger successor, and activation must
be verified on the site. Browser connection failure still prevents that action.

All heavy work is serial, with current capacity and STOP checks, owned-process
watchdogs and the daytime cutoff. Preserve preparations, source hashes and failed
attempts. Do not resume an old screen or continue blindly after an operational error.
