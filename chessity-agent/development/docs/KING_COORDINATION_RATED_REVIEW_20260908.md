# Diagnose v1.52's completed four rated games

The frozen four-game screen is complete: nominal2400 yielded0W1D1L; nominal2600
yielded0W0D2L. All three losses were checkmates, the draw threefold repetition,
and neither side had operational or clock failures. No games are added to chase
a win. These results do not establish2400 strength or justify raising opponents.

Review all173 own moves using the existing20k-node best/played screen, verifying
suspicious choices at80k/320k. The maximum requested budget is145.32million nodes
before identical-move reuse. Preserve exact match hashes, FENs, full histories,
both teacher budgets, unstable and mate-scored cases. No new JIT, games or fitting.
Then reuse those labels for the existing phase summary with zero new teacher nodes.
Find the first warning and any first stable losing transition, separately from
the terminal phase, and review squandered advantages in the draw as well.

Run only after the game controller and its children have exited. Use the hidden
Normal-priority local task, both2048MiB disk/768MiB RAM guards and STOP flags.
After analysis, publish every result and the limitations. v1.52's original tied
pair remains1W0D1L against51; its provisional selection rule is not retroactively
changed, but no overall superiority or calibrated Elo is asserted.

Engine code comes first: inspect the actual continuation that creates the
earliest relevant mistake before another search/evaluation change. Useful
learning comes second: verify counterfactual descendant targets and their
compatibility with the runtime correction range before fitting. Targeted data
come from these four games plus the two already reviewed comparison games.
No broad GM collection, repeated failed gate, blind epochs or long consistency
study is warranted. The next experiment must state a new bounded hypothesis.
