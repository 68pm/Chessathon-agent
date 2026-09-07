# Required review for every future iteration

User priority, reaffirmed 7 September 2026: engine code first, effective learning
second, targeted data after diagnosis. Every iteration must record a decision on
all three needs, including a reason when no change is warranted. Assessing all
three does not require changing all three at once: preserve a matched control so
the result can be attributed to the tested change.

1. **Engine code.** Identify the concrete missed threat, wasted search work, or
   conversion failure using actual game history and verified alternatives. Check
   legality, terminal and draw handling before evaluating strength. State the
   proposed mechanism, fixed-depth or fixed-node checks, clock budget and expected
   effect on useful search depth. For conversion work, verify the relevant endgame
   class and report whether ordinary games actually reached it. Prefer a necessary
   code repair over a training experiment that cannot address the failure.

2. **Use of training.** State exactly where learning affects a decision: root move
   preference, or evaluation of descendant positions inside search. For any network
   change, define inputs, value perspective, output scale/clipping, search integration
   and the matched control. Require numerical/runtime parity, grouped validation,
   throughput and actual game comparisons. Human explanations must become measurable
   targets such as verified successor values, move-value gaps, tactical outcomes or
   conversion outcomes. A lower training loss alone cannot justify promotion.

3. **Targeted data.** Link each requested example to a measured weakness: king
   defence, losing exchanges, pawn endings, conversion, or another audited failure.
   Start with own mistakes and verified better alternatives plus existing data.
   Record provenance, teacher budgets, history, uncertainty, rejected examples and
   opening-family partitions. Fetch external games only when a specific coverage
   gap warrants it. Name the missing pattern and resource budget before collection;
   more files or famous-player games are not themselves an improvement criterion.

Finish each review with one selected experiment, protected incumbent, immutable
candidate, declared compute/match budget, gate, completed W/D/L including every
loss, and next diagnosis. Use 120+0.5 and at most two concurrent games. No training
or teacher work during fresh final confirmation. An unchanged failed hypothesis
does not receive another cycle. Keep all exposed development groups out of fresh
confirmation and do not infer a calibrated human/site Elo from handicap settings.

The current architectural step already exists experimentally: v1.45–v1.47 use an
own-trained 768-input, 32-hidden-unit residual value network at searched descendant
positions, with incremental evaluation. This extends beyond the root policy used
by the selected v1.41. It has not yet earned promotion through playing results.
