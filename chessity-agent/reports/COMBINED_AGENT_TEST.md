# Combined Classical + Witty candidate — 6 September 2026

Created **mixed-classical-witty-v1**, with Classical's evaluation/search and the
existing Witty-trained move-preference network. Against **Stockfish's 1700 setting**
it scored **4 wins, 2 draws and 6 losses**.
Both completed batches used **30 seconds + 0.3 seconds per move**, six opening
pairs with colours reversed, 12 games per opponent. At most two games ran concurrently.

| Opponent | Candidate wins | Draws | Candidate losses | Candidate score |
|---|---:|---:|---:|---:|
| Stockfish 19, UCI_Elo 1700 | 4 | 2 | 6 | 41.7% |
| Classical v2 | 4 | 5 | 3 | 54.2% |

The direct comparison favoured the combined candidate in this small sample.
Twelve games per opponent do not establish a definitive strongest version or an
official rating. The previous Classical competition submission remains preserved.
The Stockfish number is its built-in handicap setting. Its documented calibration
uses 120+1, a different time control; see [Stockfish's UCI documentation](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-Protocol-and-Stockfish-Commands.html).

## What was combined

Classical is a programmed evaluator and search engine, with no learned dataset or
neural weights to concatenate or average. This candidate reuses that fast evaluation
and the existing Witty policy trained from the authorised history. There was no new
training run, invented dataset merge or use of benchmark results as training labels.
The policy file is byte-identical to the previous Witty candidate's policy.

The prior Witty agent ran the 300k value network throughout its hybrid evaluation.
This candidate uses classical evaluation at search nodes to recover search speed;
it retains the separately trained Witty policy at the root. The 300k value model
and its training data remain saved in the original candidate, but that value network
is not loaded by this combined runtime.

Witty move preferences receive at most **10 centipawns**. A matching Alien opening
move receives at most **15 additional centipawns**. Both are small preferences among
searched legal moves. They are bypassed under short search budgets, in check, in
late endgames and in materially unbalanced positions. Proven mate scores are unchanged.
These are search-horizon preferences, not guarantees against future tactical errors.

## Alien Gambit is optional

The repertoire can suggest the Alien move, but no longer returns it before searching.
From `1.e4 c6 2.d4 d5 3.Nd2 dxe4 4.Nxe4 Nf6 5.Ng5 h6`, the extracted package selected
**6.N5f3** in both validation runs, declining the speculative **6.Nxf7** sacrifice.
The book hint still entered search. Outside its exact recognised positions, normal
search and learned move preferences select the move.

The Stockfish batch included a Caro-Kann setup after `1.e4 c6 2.d4 d5` among its six
opening pairs. Neither player was forced into the gambit. Actual candidate Alien
sacrifice opportunities/choices: **0/0** against Stockfish and
**0/0** against Classical.
No claims of a successful Alien sacrifice are inferred from a different opening.

## Package and checks

- [Combined agent ZIP](../candidates/mixed-classical-witty-v1.zip) — 241,462 bytes.
- [Stockfish 1700 games](evidence/mixed-20260906-rating1700.pgn).
- [Direct Classical comparison games](evidence/mixed-20260906-classical_comparison.pgn).
- [Session, provenance, summaries and validation](evidence/mixed-20260906-session.json).

All **44 tests passed**, including bounded root preferences, rejection of the knight
sacrifice, mate protection and emergency-clock fallback. All **24 match PGNs** were
replayed to verify legal moves and results. Extracted-package checks made **130 legal
calls**, including **18 active policy calls**. The audit detected no runtime writes,
network use or subprocess launches. Both selective-opening checks passed.

Terminations against Stockfish: `{"checkmate": 10, "threefold_repetition": 2}`.
Terminations against Classical: `{"checkmate": 7, "threefold_repetition": 5}`.
Any ply-cap draws are reported explicitly above. The package contains the original
agent code and trained policy, with no external engine or downloaded game history.

ZIP SHA-256: `ee0f02da9613786001689673e6d68157f5965e5820efc4feea67a8bec5112e95`.

Use `Play-Combined.ps1` to play this mode locally. The candidate and earlier packages
are saved separately. The combined version has not been uploaded to the competition.
