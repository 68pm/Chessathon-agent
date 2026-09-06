# Classical + Witty Alien + Magnus Carlsen

Candidate: `candidates/classical-witty-magnus-v1.zip` (241,005 bytes).
SHA256: `6d287209c28bba520a21ef49261af99543a167fb192ce15513102c883c503a56`. Use `Play-Magnus-Mix.ps1` for local play.

Highest checkmate victories: **MadChess 1700** and **Stockfish 1700** on their nominal strength settings.
These settings and a highest individual win are not an official Elo for this agent.
The new candidate won more than it lost in the small direct comparison, but this does not establish a reliable strength improvement.

## Games downloaded and training

Collected all **9,694** completed games exposed by the named account's public index, in **66 months** and **194 parts** (maximum 50 records each), with no missing PGNs. This covers the supplied MagnusCarlsen account, not every game Magnus has played elsewhere. Private, deleted and unexposed games are outside the download.
The original JSON and PGNs remain under `data\magnuscarlsen-history`. The combined PGN is `data\magnuscarlsen-history\exports\0d8cf92395bf9fa51e63/all-available-games.pgn`.

Analysis retained **9,381 standard games** and **421,852 Magnus decisions**; 313 variant games were retained in the archive and excluded from standard-chess training. Every monthly/part checksum matched; 100 sampled Magnus labels were traced to their real source games.

The new policy uses **99,934 positions**: 50,000 Witty and 49,934 Magnus examples, after removing 66 overlapping positions. Magnus sampling includes quiet decisions without forcing-move priority; Witty retains its previous attacking-biased sample. All prior Witty splits are preserved, no exact normalized FEN is retained twice, and source games never cross splits. Related positions may still remain across splits.

The 935–64–32–1 NumPy policy has 62,017 parameters. It was initialised from the Witty-trained policy and fitted on both datasets with equal per-position weight, learning rate 0.0003, seed 20260906, up to four alternative legal moves per label. Validation stopped training after 6 epochs; epoch 3 was selected by validation cross-entropy (0.846744). Splits: 79,663 training, 9,824 validation, 10,447 test positions. Training is supervised move imitation, not self-play or 300,000 new games.

Classical has no learned dataset/weights to average: its evaluation and search remain the decision-making component. The newly fitted neural policy supplies a bounded 10-centipawn root preference; optional Alien preparation supplies up to 15 more. Search considers all legal moves, and proven mate scores remain unchanged. The earlier 300k value network is preserved separately and is not loaded in this package. All runtime code/configuration is byte-identical to the previous combined candidate; the policy weights changed.

## Held-out move agreement

Each cell uses the same 1,000 held-out positions for both models; these are raw network choices before search, not engine accuracy percentages or Elo.

| Player samples | Previous top 1 | New top 1 | Previous top 3 | New top 3 |
|---|---:|---:|---:|---:|
| magnuscarlsen | 24.8% | 28.6% | 46.7% | 52.4% |
| witty_alien | 43.0% | 45.2% | 68.7% | 69.2% |

## Fixed match results

| Opponent | Wins | Draws | Losses |
|---|---:|---:|---:|
| madchess:900 | 2 | 2 | 0 |
| madchess:1000 | 4 | 0 | 0 |
| madchess:1100 | 3 | 0 | 1 |
| madchess:1200 | 4 | 0 | 0 |
| madchess:1300 | 1 | 0 | 3 |
| madchess:1400 | 0 | 1 | 3 |
| madchess:1500 | 2 | 0 | 2 |
| madchess:1600 | 0 | 1 | 3 |
| madchess:1700 | 1 | 1 | 2 |
| madchess:1800 | 0 | 0 | 4 |
| madchess:1900 | 0 | 1 | 3 |
| madchess:2000 | 0 | 0 | 4 |
| madchess:2100 | 0 | 0 | 4 |
| madchess:2200 | 0 | 0 | 4 |
| madchess:2300 | 0 | 0 | 4 |
| madchess:2400 | 0 | 0 | 4 |
| madchess:2500 | 0 | 0 | 4 |
| stockfish:1700 | 3 | 3 | 6 |
| previous:None | 5 | 5 | 2 |

All 92 games used 30 seconds plus 0.3 seconds per move per side, at most two simultaneous games, with fresh processes. Each MadChess rung used both colours from the starting position and after `1.e4 c6 2.d4 d5`. Stockfish 1700 and the previous combined candidate each used six colour-paired openings. The full schedule and candidate hashes were frozen before outcomes, with no retries chosen to chase a win.

All 92 PGNs were replayed and their results checked. Terminations: `{"threefold_repetition": 13, "insufficient_material": 1, "checkmate": 78}`. Alien sacrifice opportunities in these games: 0; sacrifices chosen: 0. The package check independently confirmed that its optional preparation can decline `6.Nxf7`, choosing `6.N5f3` in the standard test position.

## Verification and limits

49 unit tests passed; the extracted competition ZIP passed 130 legal-move calls, including 18 active-policy calls in the 30-call longer-clock audit. Both package audits verified optional Alien integration, memory below 2 GB, and no runtime writes, network access or subprocesses. Local Windows tests do not replace the organiser's Linux validation. No external engine, third-party engine weights or game archive is included in the candidate.

The prior combined ZIP and selected classical `submission.zip` are preserved. A disk-space failure occurred before fitting; temporary derived feature/shard caches were removed, the failure log was retained, and training then completed. Training samples, source archives, model checkpoints and results remain available; feature caches can be regenerated for resume.

MadChess settings are not calibrated to a verified human rating pool. Stockfish's handicap calibration also depends on its test conditions; 30+0.3 games here are not a Chess.com, FIDE or competition rating. Four games per MadChess level and twelve against each other opponent leave substantial uncertainty. Better imitation does not establish stronger tactical search or better endgame play.

## Reproducibility and sources

Full evidence: `docs/evidence/magnus-mixed-20260906-session.json`, `docs/evidence/magnus-mixed-20260906-games.json`, and the three opponent-family PGNs. Highest winning games: `docs/evidence/magnus-mixed-20260906-highest-wins.pgn`.

The user's previous confirmation of written Chess.com authorisation and the present instruction to download/train on this account are the recorded authorisation basis. The grant text was not independently inspected. Collection used the documented public API serially with caching and delays.

- [MagnusCarlsen account](https://www.chess.com/member/magnuscarlsen)
- [Chess.com public API](https://www.chess.com/news/view/published-data-api)
- [MadChess strength calibration FAQ](https://www.madchess.net/the-madchess-uci_limitstrength-algorithm/limit-strength-faq/)
- [Stockfish UCI options](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-Protocol-and-Stockfish-Commands.html)
