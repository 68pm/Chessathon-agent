# New source-group check of the rejected value model

Use the frozen rule-value-01 model and its already selected blend exactly once
on the new independently labelled D65 descendants. Do not train, retune the blend,
select phases or change any runtime from these results. The original static gate
and its rejected status remain unchanged whatever this diagnostic finds.

Before inference, exclude exact/mirrored collisions with the model's recorded
training positions. Keep the entire D65 pair in one group. Validate the checkpoint
loader against saved earlier predictions, including its stored centipawn scale,
and the readable classical evaluator against recorded old baseline values.

Report classical versus frozen-model absolute error by game and phase, including
every worsening result. These selected error descendants provide new diagnostic
evidence about generalisation; they do not measure chess strength. Any later
revised model needs another reserved assessment after these results are examined.
