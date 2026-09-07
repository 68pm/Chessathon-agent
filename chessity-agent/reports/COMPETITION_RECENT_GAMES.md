# Actual competition games — rounds 54–56

The latest three completed games were saved with every move and clock reading;
the full 21-game CSV summary is archived locally. Older rounds are not attributed
to the current model. The dashboard's upload 5 (7 September 15:56 local) and
upload 6 (18:18 local) both display hash e4b66bd0f5a1, matching local v1.41.
These three games fall after the first such upload and have 24.4–26.0-second
initialization times. Their v1.41 mapping is inferred from that evidence; a full
per-game artifact hash was not exposed. Earlier upload 4 matches v1.14.

| Round | Opponent | Colour | Result | Website accuracy / ACPL |
|---|---|---|---|---|
| 54 | Wilson's | Black | Checkmate win | 93.0% / 22 |
| 55 | Stock-ish | White | Checkmate win | 92.7% / 20 |
| 56 | drunkenmaster | White | Fifty-move draw | 96.0% / 10 |

The website analysis uses Stockfish 16 at depth 16. Accuracy is its own metric,
not an Elo estimate. The account's earlier aggregate rating includes older bots;
two wins and a draw do not establish the new version's stable rating.

All three imported games passed legal-move, outcome and clock checks, including
CSV move-count, time-used and final-clock parity. Individual browser download
actions did not yield accessible PGN files, so the complete PGNs were extracted
from their observed DOM download links. Compact checksums verified the transfer;
clock comments were restored from exact integer milliseconds. PGN formatting was
normalized without changing the moves or clocks. The CSV downloaded normally.

Offline Stockfish 19 then screened all 194 own moves at 20k nodes, with suspicious
decisions verified independently at 80k and 320k nodes. It found three stable
errors of at least 200 centipawns, all in the two wins and all in the middlegame:

* Round 55, 26.Kf1: gives back a winning advantage by allowing ...Nxe1. R(e1)c1
  preserves it. Verified losses versus the better choice were 492 and 524 cp,
  with about 50 seconds on Chessity's clock.
* Round 54, 33...Bxc3: 34.bxc3 is a stronger defensive response than the one the
  opponent played. ...R(c7)b7 retains the advantage. Verified regret: 394/366 cp,
  with about 33 seconds left.
* Round 54, 36...Be8: ...e3 keeps the position defensible. Verified regret:
  263/374 cp, with about 28 seconds left.

Round 56 had no stable 200cp error and no verified loss of a winning advantage
under this finite analysis. Its draw should not automatically be blamed on
conversion. The next useful target is tactical defence and stronger-opponent
recaptures in the middlegame, including mistakes hidden by eventual wins.

These positions are development material. They have not trained the network yet
and cannot later be reused as fresh strength evidence. The capture-ordering pilot
failed its earlier gate, so its code is not in the recommended upload. v1.41 remains
selected while the next change is diagnosed and measured.

Game sources: [round 54](https://aichessathon.com/game/9a1a16e4-c938-432c-9563-7b619f338914),
[round 55](https://aichessathon.com/game/29202c02-a841-464b-9341-e43602be75d1),
[round 56](https://aichessathon.com/game/319f2f56-c21d-4d8d-a3a6-edc6643a12d3).
