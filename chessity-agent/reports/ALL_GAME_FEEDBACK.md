# Learning from every game

Every future local match should use `scripts.feedback_matches`. It accepts the
same arguments as the existing match runner and adds a required review and
learning checkpoint after each saved game, before another game begins. On
restart it finishes any outstanding review without playing that game again.
The candidate's playing files stay frozen throughout each comparison.

For downloaded competition games, pass a completed JSON record containing all
games to `scripts.feedback_batch --source <games.json> --out <new-directory>
--initial-policy <current-candidate>/models/player-policy.npz`. Each game must
include its PGN, our colour, source game identifier and honest version label.
This is an import workflow; it does not silently scrape authenticated games or
change the competition submission.

## Rewards and corrections

Every own move receives Stockfish review at 80,000 and 320,000 nodes, using its
actual PGN history. The teacher compares unrestricted best play with the played
move at the same root. A best move already found in the unrestricted search
reuses that result. Complete evaluations are cached by teacher hash, settings,
starting position, history, restricted move and budget.

- A move within 25 cp of the best at both budgets earns a positive signal.
- A loss of at least 70 cp at both budgets earns a negative signal, bounded to
  −1; at least 200 cp is recorded as a major mistake.
- Smaller differences, inconsistent evaluations and forced moves do not create
  confident learning targets. If the two budgets disagree on the corrective
  move, the negative signal is recorded but that correction is not fitted.
- Mate scores remain categorical. Preserving an engine-supported mate earns a
  positive signal; missing a mate or allowing one earns a negative signal when
  both budgets agree. Already forced-losing positions are not punished again
  simply because they remain lost.
- Wins, draws and losses are all reviewed. Outcome and opponent rating do not
  enter the reward calculation. A salvaged draw can contain good defence; a win
  can contain blunders. The labels are engine estimates, not perfect proof.

All moves and uncertain positions remain in the annotated PGNs and JSON review.
Basic tags identify phase, checks, captures, promotions and preservation of an
estimated advantage; they do not invent strategic explanations from the result.

## Fitting and limits

The existing 935-input / 64 / 32 / 1 move-policy network receives one bounded,
reward-weighted supervised update. Good moves are reinforced; negative examples
prefer the independently verified better move. The existing policy anchors the
update, with up to 128 earlier training positions for broad replay. Sampling
keeps both reward signs and caps each game at 48 fitted examples so a long easy
win does not dominate a short loss. Every move is reviewed even if it is not
selected for that bounded fit.

History-dependent repetition decisions remain search regression examples and
are excluded from this policy's weights because its features omit repetitions.
Root rewards are never inserted as static position values. Independent quiet
descendant labels remain the input for later value-network work.

A saved checkpoint is not a stronger released agent. Record the training
objective, validate changed move choices and run a small practical comparison
before promotion. Training examples cannot subsequently be called an independent
rating test. The selected competition ZIP and its read-only behaviour stay
unchanged by the feedback pipeline.

This implementation runs locally between games, one teacher process at a time.
It retains the 2048 MiB disk / 768 MiB RAM launch guards and the user's STOP flags.
It creates no recurring automation. Downloaded games enter the same process when
they are available locally.
