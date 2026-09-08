# Learning from the new competition games — 8 September 2026

The three newly downloaded Chessathon games scored **2 wins, 0 draws, 1 loss**.
The dashboard displayed a **1666 competition rating** and an active upload hash
prefix matching the archived **v1.41**. These are competition results for that
submission context, not a rating for the newer v1.53 or experimental networks.

The new feedback pipeline reviewed **8 games and all 395 of our moves**:
those three new games, the latest competition draw, and four local experimental
rematch losses. Every move received 80k and 320k Stockfish review with its actual
history. Wins do not automatically produce positive labels; losses do not
automatically make all their moves bad.

| Game | Result | Our moves reviewed | Positive signals | Negative signals |
|---|---|---:|---:|---:|
| Chessathon round 70 | Win | 43 | 23 | 1 |
| Chessathon round 71 | Win | 62 | 39 | 5 |
| Chessathon round 72 | Loss | 29 | 8 | 3 |
| Chessathon round 68 | Draw | 73 | 42 | 6 |
| Experimental local game 1 vs 2400 | Loss | 49 | 18 | 3 |
| Experimental local game 2 vs 2400 | Loss | 21 | 5 | 2 |
| Experimental local game 3 vs 2600 | Loss | 86 | 29 | 7 |
| Experimental local game 4 vs 2600 | Loss | 32 | 9 | 6 |

Total: **173 positive and 33 negative signals**.
The remaining decisions were forced, already losing by engine mate estimates,
small differences or uncertain evaluations. They remain in the review files.

## What to reinforce and correct

- **Round 70 win:** 14...Bxh3, 21...Qe4 and 25...Bd5 preserved substantial
  advantages. The queen–bishop coordination was useful. However, 15...Bb4
  cost 100 / 141 cp compared with 15...Qd7.
- **Round 71 win:** 30.Nf6+ and the passed-pawn advances 32.c6 and 33.c7
  received positive signals. But 34.Qf4 lost 255 / 316 cp compared with
  34.Qc5. Winning this game does not erase the missed stronger conversion.
- **Round 72 loss:** 9...cxd5 lost 237 / 247 cp versus 9...O-O. The game
  later recovered: 13...Rb6 and 14...Ra6 were supported moves, and the
  position was roughly equal before 24...Qc3+. The deeper check below
  confirms that 24...Ra5 held the position while the check lost 531 / 587 cp.
  That later error was excluded from the first fit because its initial
  labels were unstable. The confirmed correction is saved for the next fit;
  this loss is not attributed solely to the early castling mistake.
- **Recent draw:** all 73 of our moves were reviewed, including defensive
  moves and repetition history. Do not remove draw acceptance as a blanket
  fix. History-dependent examples remain search checks rather than being
  fitted into a policy that cannot represent repetition.

## Actual learning and current upload

The pipeline fitted **190 move-policy examples**: 166
reinforced good moves and 24 verified corrections, with
128 earlier positions anchoring the existing policy. It made
one epoch / 20 bounded optimizer updates. The recorded training
objective changed from **1.363606 to 1.336934**.
This is a training objective, not a new Elo rating or proof of stronger play.

The checkpoint changes the existing neural move policy. It does not replace
the classical position evaluator or solve search weaknesses by itself. Quiet
descendant positions still need independent value labels before value-network
training. The three priorities remain engine code, useful value learning,
and targeted examples from diagnosed mistakes.

**v1.53 remains the recommended upload.** The earlier descendant-network
experiment lost both games at 2400 and both at 2600; 2800 was not triggered.
The new reward-policy checkpoint has not established stronger playing results
and has not been promoted. No new version or replacement upload is claimed.

## Small playing-search check

The fitted policy changed **1 of 12 moves** in the one-second
comparison with v1.53, with the policy enabled in both processes. Both builds
returned legal moves and preserved the full board history within the time bounds.
Mean evaluation loss at 80k / 320k nodes: baseline **74.42 / 81.42 cp**;
fitted policy **84.42 / 91.00 cp**.
The predeclared quality gate **failed**.
These are exposed development positions. They do not establish Elo, and a
passing position gate alone does not replace the upload.

### Deeper review of the late round 72 error

After the frozen fit, the move 24 position received a separate 1.28M-node
best/played review, paired with the existing 320k analysis. The original
uncertain review and fitted model remain unchanged.
The refined classification is **major_mistake**, reward **-1.0**.
Best values from Black's perspective: [-21, -3] cp;
played values: [-552, -590] cp.
This refinement is saved for the next training batch; it was not part of
the checkpoint already fitted above.

## Future games

The default `scripts.feedback_matches` runner reviews and saves a learning
checkpoint after every local game, including wins and draws. The playing
candidate stays frozen during a comparison. Saved markers prevent duplicate
review/fitting on restart. Downloaded competition PGNs use `feedback_batch`.
The pipeline runs offline between games and keeps runtime inference read-only.
Ten tests passed, including numerical reward gradients, mate handling, exact
history, mixed-version identity and replay-safe completion markers.

The PGN bundle includes the original games and annotations with verified
alternative continuations. Raw teacher values and uncertainty remain in JSON.
No long consistency study or recurring automation was started.
