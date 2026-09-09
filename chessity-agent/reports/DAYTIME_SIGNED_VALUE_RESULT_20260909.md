# Signed value trial: rejected, v1.54 retained

The fresh pawn-screen descendants produced 26 eligible independent values from
27 candidates at 80,000 and 320,000 Stockfish nodes. The labeller requested ten
million nodes and preserved one unstable/excluded endpoint. Histories are kept;
root move rewards were not copied into value labels.

The new learner used 67 targeted positions, 12,000 broad training positions and
1,200 development-validation positions. Its eight hidden units had four fixed
positive and four fixed negative readouts. Sixteen epochs performed 752 updates.

The lowest raw validation capped squared error was 82,832.59 cp squared, against
96,939.56 for the classical evaluator. However, no epoch/blend passed the separate
positive- and negative-correction cohort checks. The retained blend is therefore
zero: no neural correction is selected. Per-epoch cohort statistics were not
saved, so the output does not establish which cohort failed each epoch or why.
Do not infer a diagnosis beyond that recorded limitation, or call the raw mean
error gain a successful evaluator improvement.

The candidate was rejected before any new held-out teacher work. Its reserved
roots were not independently labelled in this trial. No runtime integration or
new playing-strength games are justified for this rejected fit. The selected
v1.54 remains byte-identical, with its existing learned root policy and classical
searched-position evaluator. The trial's saved value file is experimental and
must not be substituted into the release.

Evidence: `runs/daytime-20260909/signed-targets-01/`, `signed-value-01/`, and their
separate bounded supervisor records. All attempts are preserved. The next useful
work is analysis of fresh competition games and a bounded defensive search trace;
another unchanged fit would not resolve the failure.
