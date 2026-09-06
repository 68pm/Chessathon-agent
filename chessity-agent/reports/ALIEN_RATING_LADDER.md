# Alien Gambit rating ladder — completed 2026-09-06

The highest setting defeated was **MadChess 3.4 at nominal 1500 Elo**. At that level the candidate scored 1 win, 0 draws and 2 losses.

All **51 games** finished: **14 wins, 6 draws, 31 losses**.
Each listed setting was tested 3 times. Highest setting with a
majority score across its games: **1300**.

These are MadChess's built-in difficulty labels. Its author explicitly says their
human-rating calibration is unknown. Beating one setting does not give the candidate
that Elo. This opening-only result does not replace the earlier general-position
Stockfish estimate or demonstrate an improvement from training.
See [the author's calibration explanation](https://www.madchess.net/the-madchess-uci_limitstrength-algorithm/limit-strength-faq/).

| MadChess nominal Elo | Agent wins | Draws | Agent losses |
|---:|---:|---:|---:|
| 900 | 3 | 0 | 0 |
| 1000 | 2 | 1 | 0 |
| 1100 | 3 | 0 | 0 |
| 1200 | 2 | 1 | 0 |
| 1300 | 2 | 1 | 0 |
| 1400 | 1 | 0 | 2 |
| 1500 | 1 | 0 | 2 |
| 1600 | 0 | 2 | 1 |
| 1700 | 0 | 1 | 2 |
| 1800 | 0 | 0 | 3 |
| 1900 | 0 | 0 | 3 |
| 2000 | 0 | 0 | 3 |
| 2100 | 0 | 0 | 3 |
| 2200 | 0 | 0 | 3 |
| 2300 | 0 | 0 | 3 |
| 2400 | 0 | 0 | 3 |
| 2500 | 0 | 0 | 3 |

## What was tested

Candidate: `witty-300k-hybrid-v1`, the existing 300k-position hybrid plus the
Witty_Alien move-preference network trained using the 50,000 sampled decisions.
The weights, search and opening repertoire were frozen throughout this ladder.
No new training or promotion of the default competition engine took place.

The starting line comes from [Witty_Alien's downloaded game](https://www.chess.com/game/live/89455820377)
on 2023.09.26:

`1.e4 c6 2.d4 d5 3.Nd2 dxe4 4.Nxe4 Nf6 5.Ng5 h6`

Those ten plies are opening setup. The candidate then independently chose **6.Nxf7
in all 51 games**, using its enabled prepared repertoire. MadChess accepted the sacrifice
with **6...Kxf7 in 51 games**. Every subsequent move was played by the engines;
the historical game's remaining moves were not replayed. The position was present
in the policy training data; this is a deliberate repertoire test, not a held-out
position test. The prepared move and the learned policy have separate roles.

Both engines had **30 seconds + 0.3 seconds per move** from the setup position.
The candidate was White in every game. Up to 2 games ran concurrently on this computer,
with fresh engine processes each game. MadChess used its untouched release config,
64 MB hash and `UCI_LimitStrength=true`; only `UCI_Elo` changed between levels.
Its advertised supported range was 600–2600.
There was no custom weakening, depth override or substituted rating scale.
MadChess's default randomization has no exposed seed setting, so reruns may differ.
The schedule was fixed before results were known, with no extra attempts to chase a win.

## Verification and files

All 51 PGNs were independently replayed to verify legal moves, final positions,
results, the Alien sacrifice and the complete schedule. No invalid games occurred.
Terminations: `{"checkmate": 45, "fifty_moves": 2, "threefold_repetition": 4}`.
The configured cap was 400 played plies after setup; 0 games reached it.
Candidate file hashes still match the manifest saved before play.

- [All games in PGN](evidence/alien-ladder-20260906.pgn)
- [Full results, timings, hashes and replay audit](evidence/alien-ladder-20260906.json)
- [Victories at the highest defeated level](evidence/alien-ladder-20260906-highest-wins.pgn)

The external opponent was obtained from the [official MadChess download page](https://www.madchess.net/downloads/).
It is stored only among local benchmark tools and is not inside the candidate or submission.
Opponent executable SHA-256: `248a200fa15d851d8e81d583a19d7830b21e7d04daa5237ebf689dde10743407`.
See the [official strength-setting documentation](https://www.madchess.net/the-madchess-uci_limitstrength-algorithm/).

To repeat the same ladder on this computer with a fresh output folder:

```powershell
.\Test-Alien-Ladder.ps1
```

The original default competition submission remains unchanged.
