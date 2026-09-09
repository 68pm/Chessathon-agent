# Conditional short screen of per-ply array reuse

Prepared before timing/quality results. Start only after move-buffers-01 passes
its exact-work efficiency gate and independent clock-choice review, and both
controllers and all owned workers close. A correctness pass alone is insufficient.

Validate the exact ZIP in the strict read-only harness, then play one pair at
120s + 0.5s against exact v1.55, exact v1.53, nominal 2400 and nominal 2600, using
both colours and the existing development openings/offsets. A clean played 2600
win and at least one point in that pair permit a further 2800 pair. Review every
game through the unchanged Windows feedback wrapper with frozen playing weights.

Keep the established selection gate: >=1.5/2 against v1.55, >=1/2 against v1.53,
and no operational failure anywhere. Inspect all results before release. This
small development comparison does not establish calibrated Elo or reliable
rating superiority. Reward-policy checkpoints remain experimental.

The afternoon controller has a predeclared 6000-second overall screen bound,
with a start requirement of more than 6300 seconds before the heavy-work cutoff.
Each pair retains its existing 1500-second limit and remaining-time check. A slow
partial screen is preserved and cannot qualify a release; do not extend a bound
or omit an adverse result to select it. Keep capacity and STOP safeguards.

Only a complete qualifying screen and separate release audit permit replacing
v1.55. Automatic competition upload is authorised, but site validation and active
version must be observed. The current browser failure still blocks that action.
