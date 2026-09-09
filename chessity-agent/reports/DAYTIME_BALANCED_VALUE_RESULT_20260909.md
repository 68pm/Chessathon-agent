# Balanced value trial: rejected after unused descendant evaluation

The trial completed in 24.09 seconds, including preparation, 752 gradient
updates and 11.12 million requested teacher nodes. All 16 epoch checkpoints and
per-blend positive/negative validation-cohort errors are retained.

The selected development checkpoint was epoch15, blend0.5. Broad capped MSE
improved 96939.56 to 85160.29 cp squared. Negative-correction validation MAE
improved 202.81 to 201.06 cp; positive-correction MAE improved 281.63 to 253.38 cp.
Target MAE improved 212.54 to 126.44 cp and the 32 newly labelled, filtered
descendant targets improved 256.64 to 149.56 cp. There were 97 target positions
after deduplication and 13297 total training/development rows.

The frozen weights then failed the predeclared unseen-descendant gate. Of 24
unused reserved roots, 22 produced eligible independently labelled descendants.
Mean absolute error increased 283.18 to 286.50 cp; errors of at least 200 cp
remained 12. The failed gate was mean error, not a lack of eligible examples.
Those 24 roots and their descendants are now exposed and cannot be reused as
fresh evaluation in a later experiment.

On these 22 descendants the model added more than 1 cp in 18 cases and subtracted
more than 1 cp in four, with a mean addition of 63.44 cp. Independently labelled
corrections needed increases of at least 25 cp in nine cases, decreases of at
least 25 cp in nine, and less than 25 cp either way in four. These use different
thresholds, so they are a diagnosis of directional bias, not a confusion matrix.
Balanced sampling helped the development cohorts but did not ensure transfer.

No runtime candidate was made. The selected v1.55 still uses its classical
searched-position evaluator and original policy. Frozen failed weights have SHA256
`65dd01fc8d0c04f5e960ae2dc98dd04d98fcc73e7ebc31527c4f56110d35edee`.

A possible next architecture is a difference between the two existing relative
piece perspectives, making the positional correction antisymmetric and removing
its common positive component. This is a testable constraint, not a demonstrated
fix: actual chess value also depends on whose turn it is. Do not create synthetic
teacher labels by reversing the side to move. Test any changed architecture on
new reserved descendants and measure its runtime cost before making a release.
