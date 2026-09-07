# Residual learning pilot: no promotion

The original 768–32–1 residual evaluator finished **2W/4D/2L against its matched
compiled classical control**, **1W/0D/3L against nominal 2400**, and **0W/0D/4L
against nominal 2600**, at 120+0.5. All 16 games passed schedule, frozen-runtime,
legal-move, clock and outcome replay checks. There were no candidate runtime failures.

The static validation MSE reduction of about 19.4% did not produce a demonstrated
playing-strength gain. The matched comparison's four colour pairs are inconclusive;
the rated screens are also small, and use different openings from cycle 01. Their
differences cannot isolate a causal effect of the network. The network is preserved
as an experimental checkpoint, and is not selected for the current confirmation.

Inspection of the supplemental training path found a coverage gap: the 74 eligible
own-game examples encode the position before a mistake and its teacher-best value.
They do not explicitly pair the mistaken move's successor with the teacher's better
continuation. A value evaluator trained on those root labels may improve static error
while still failing to distinguish the decisions that actually lost our games.
That is a testable hypothesis, not an established explanation of every loss.

Next data pilot, declared before labels: after the current frozen confirmation and
its error audit finish, sample at most 16 verified large-error roots, at most two per
game, in chronological round-robin order across games. Reconstruct each full history.
For the played and teacher-preferred branches, take the immediate successor or follow
at most four recorded PV plies to leave check. Independently relabel both endpoints
at 80k/320k nodes. Keep only nonterminal, non-check states with adequate draw-clock
margin, finite stable scores, preserved branch ordering, and no protected validation
collision. Quarantine uncertain or mate-scored examples. Budget at most 12.8 million
teacher nodes; no new fitting until coverage and label quality have been reviewed.

This supplies decision-related value targets and pairing metadata. It does not
pretend a win makes every earlier move correct, and it is not policy-gradient RL.
The next learner should compare an equal-budget broad-data control with a modest
counterfactual replay mixture, keep epoch zero eligible, and require move-quality
and matched-game evidence in addition to static validation. Architecture changes or
new external GM games need a measured coverage reason, rather than another blind fit.

Current confirmation games must finish before any teacher work begins. Once their
rated games are used for learning, their four opening groups are retired as development
material. Future confirmations need different groups/positions. No target achievement
or human/site Elo claim follows from this pilot.
