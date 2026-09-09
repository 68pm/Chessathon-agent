# Bounded curriculum planning while matches remain frozen

The existing feedback runner already reviews every completed game and fits a
separate experimental move-policy checkpoint. This addition prepares position
examples for the new781-feature value architecture without changing that runner,
its playing weights, or the current match schedule. Planning is light Python
work; independent endpoint labelling and fitting must wait until all active
engine work has stopped and the remaining overnight budget permits it.

Use only completed reviews. Replay histories and verify their moves, SAN, colour
and deterministic two-budget reward classifications. Report every game's error
counts by phase and retain its candidate version and opponent separately. Game
outcome and opponent rating never select a target or determine a move reward.

Choose at most three confidently labelled mistakes where both best-position
estimates are at least-300cp: first recoverable error, largest recoverable error,
and earliest missed conversion from at least+150cp. Fill unused mistake slots
with remaining recoverable errors. Late mistakes in already lost positions
remain in the phase diagnosis instead of dominating the curriculum.

Retain at most two independently supported good moves from different phases,
preferring middlegame then endgame then opening. Within each phase prefer moves
preserving an evaluated advantage, then take the median chronological example.
This fixed recipe is declared before reviewing the new comparison results.

From the selected roots, propose quiet endpoints after2 or4 plies of the saved
stronger-budget best and played continuations. Each endpoint will need its own
80k/320k analysis; no root value or reward becomes a leaf label. Exclude checks,
terminal/draw claims, repetitions, draw clocks>=70 and existing targeted/broad
model-training keys. Preserve exclusions. Deduplicate mirrored positions with
validation priority. There are at most20 proposed endpoints per game.

Keep all games sharing a starting position or its colour mirror together,
ignoring move counters when grouping. Assign held-out groups by
a fixed salted group hash before endpoint labels, reserving at least one group;
with only one group the entire group is diagnostic validation, so fitting is
not justified. Exposed source games and targeted replays are development data,
not new playing-strength validation. Check other training corpora for collisions
again if the training recipe later expands beyond the recorded inputs.

Mark whether the guarded runtime would actually use a learned correction at
each endpoint. Opening-root searches and low-material endings remain classical;
their examples are evaluator/search diagnostics, not evidence that updating the
currently gated network will fix those phases. Preserve source hashes, the
read-only release, and all previous failed experiments.
