# Chess agent

The [GitHub repository](https://github.com/68pm/Chessathon-agent/tree/main/chessity-agent)
preserves the chronological builds; v1.41 is selected; the earlier v1.41 confirmation remains separate. v1.35 is an archived failed preflight. See the previous
[35-version delivery and download details](docs/DELIVERY.md).

## Autonomous improvement programme — active

**Selected upload: chessity-agent v1.41**, available at `../chessity-agent.zip`.
The current priority is [quick competition improvements](docs/COMPETITION_FAST_TRACK.md)
before 11 September. The [latest four-game diagnostic](docs/COMPETITION_QUICK_CHECK_01.md)
finished 0W/0D/2L at nominal 2400 and 1W/0D/1L at nominal 2600. This is a separate,
small local sample, not a new rating or dashboard result. Older competition games
used older agents; prioritize the latest matches with verified version provenance.

The [latest three analysed competition games](docs/COMPETITION_RECENT_GAMES.md)
scored2W/1D/0L. Their v1.41 attribution is inferred from upload timing and displayed
hashes. Three verified middlegame errors in the wins now guide development.
[Cycle10](docs/IMPROVEMENT_CYCLE_10.md) failed its tactical gate;
[cycle11](docs/IMPROVEMENT_CYCLE_11.md) preserved exact scores but gained only4.6%
speed. Neither changed the selected download. [Cycle12](docs/IMPROVEMENT_CYCLE_12.md)
also missed its speed gate. [Cycle13](docs/IMPROVEMENT_CYCLE_13.md) passed exact
fixed-work, speed and read-only checks. Its legal-pawn proof candidate
finished 0W/1D/1L against41 at120+0.5. Selected download: v1.41; no long study.

v1.41 scored **23W/1D/0L against v1.14**, **3W/4D/1L at nominal 2400**, and
**0W/3D/5L at nominal 2600** in the fixed 40-game confirmation at 120+0.5.
It passed the predeclared promotion rule and all reliability checks. These results
do not establish consistent 2600 strength or a human/site rating. The improvement
programme remains active. See [current results and download](docs/IMPROVEMENT_RESULTS.md).

See [cycle findings](docs/IMPROVEMENT_CYCLE_01.md),
[the completed residual-learning critique](docs/IMPROVEMENT_CYCLE_02.md),
[the continuing loop](docs/IMPROVEMENT_LOOP.md), and
[the predeclared independent confirmation](docs/IMPROVEMENT_CONFIRMATION_01.md).
The improved engine uses our own Python source, compiled in memory by the permitted
Numba runtime, with optional exact elementary endgame tables. No external engine code
or pretrained chess network ships. Its package passed strict read-only inference;
the earlier full suite passed **108 tests**. Subsequent experiment checks are
recorded individually in their cycle reports. Use Python 3.12 and
`requirements-compiled.txt` for this separate development environment.

<!-- ELITE_SESSION_START -->
## Earlier phase and elite selection: chessity-agent v1.14

That earlier delivery selected v1.14, preserved at `candidates/classical-witty-magnus-v1.zip`. The phase and elite-learning experiments did not earn promotion. The final outcome candidate (v1.33) scored 1W/1D/14L at 2400 and 0W/5D/11L at 2600; its direct score against v1.14 was 5W/2D/9L. Neither consistency target was reached. Clock: **120+0.5**; read-only runtime checks passed.

The neural policy really was trained from 20 independently verified elite cases and prior replay, with per-game Stockfish review and bounded outcome supervision. The referenced full elite corpus was unavailable. See [that historical 35-version delivery](docs/DELIVERY.md), [elite results](docs/ELITE_LEARNING_RESULTS.md) and [phase results](docs/THREEPHASE_RESULTS.md). Training-case recognition is not a rating, and the newer version number does not establish a stronger agent.
<!-- ELITE_SESSION_END -->

Earlier fusion selection and its dated results are preserved in `docs/FINAL_FUSION_RESULTS.md`.

<!-- MAGNUS_SESSION_START -->
## Magnus + Witty + Classical candidate

`candidates/classical-witty-magnus-v1.zip` adds a newly fitted neural move policy
trained on 99,934 positions from both players, using the unchanged
classical search and optional Alien preparation. Downloaded 9,694 available Magnus
games in 194 parts. In the fixed 92-game test, the highest checkmate victories were
MadChess 1700 and Stockfish
1700 nominal settings. Against
the previous combined agent it scored 5W/5D/2L.
The new candidate won more than it lost in the small direct comparison, but this does not establish a reliable strength improvement.
See `docs/MAGNUS_MIXED_SESSION.md` for training, every rung, PGNs and limitations.
Use `Play-Magnus-Mix.ps1` for local play. Previous packages remain available.

<!-- MAGNUS_SESSION_END -->

An original Python chess engine, a small neural framework, trained experimental weights,
and local AI Chessathon packaging. **The default competition runtime is classical search.** The first neural
and style candidates did not earn promotion in paired matches. This is a tested starting
engine, not an established advanced or master-strength engine. Rating evidence and its
limitations are recorded in `docs/RATING_AND_300K.md`.

## Combined Classical + Witty candidate

`candidates/mixed-classical-witty-v1.zip` combines Classical's fast evaluation with
the existing Witty-trained move policy. Alien Gambit preparation is a bounded
search preference; the sacrifice can be declined. No new model fitting took place.
It scored **4W/2D/6L against Stockfish's 1700 setting** and **4W/5D/3L against
Classical v2**, at 30+0.3. The small direct-match edge does not establish a clear
strength gain or a new Elo. Both packages remain available, and the selected
Classical submission is preserved. See `docs/COMBINED_AGENT_TEST.md` for the full
results and validation. Use `Play-Combined.ps1` for local play.

## Unattended training

The 100k and 300k runs completed on 2026-09-05 at 17:31 London time. Each trained
64- and 128-unit models and completed package and paired-match checks. No candidate
passed promotion; all checkpoints and results are saved. The 300k hybrid is available
for local play, with an optional Alien Gambit repertoire. See `MODEL_CARD.md`.

```powershell
.\Play-300k.ps1
.\Play-Alien.ps1
```

The first gives you White against the trained hybrid. In Alien mode the engine plays
White and you play Black. It enters the gambit if you follow the relevant Caro–Kann
line. This is a speculative attacking option; see `docs/ALIEN_GAMBIT.md`.

## Trained player-style candidate

`Play-Trained-Aggressive.ps1` runs the 300k hybrid with a separate move-preference
network trained on 50,000 decisions sampled from the authorised Witty_Alien history.
`Play-Alien.ps1` now uses this candidate when available; `-Original` keeps the earlier
prepared-repertoire version. Both play White with the Alien Gambit enabled.
See `docs/WITTY_TRAINING_SESSION.md` for the completed training and fresh rating evidence.
The download retains 166,438 available records in 3,329 parts under
`data/witty_alien-history/`.

## Completed Alien Gambit ladder

The Witty-trained candidate played 51 games against MadChess 3.4, three at each
nominal setting from 900 to 2500. Its highest victory was at **1500** (one win,
two losses at that level); it scored 14 wins, six draws and 31 losses overall.
Every game began from the same verified Witty_Alien opening position, and the
candidate chose `6.Nxf7` in all 51 games. These are opponent difficulty settings,
not a new rating for the agent. See `docs/ALIEN_RATING_LADDER.md` for the full table,
replay-verified PGNs and limitations. Use `Test-Alien-Ladder.ps1` to repeat locally.

## Start here on this computer

For resumable game-history collection and automatic style analysis, use
`Download-Player-Games.ps1`. It saves up to 50 games per part and prepares move-learning
examples. See `docs/GAME_DOWNLOADER.md` for usage and the recorded user confirmation
of written Chess.com authorisation.

Open PowerShell in this folder. The session's Python 3.12 environment is already ready.

```powershell
.\run.ps1 play
.\run.ps1 analyse --seconds 2
.\run.ps1 test -q
.\run.ps1 train --out runs/my-next-training --epochs 16
.\run.ps1 package
```

`play` gives you White and accepts moves such as `e4` or `e2e4`. Type `quit` to stop.
`analyse --fen "<FEN>" --seconds 2` analyses a position. Training runs locally at no API
cost. The existing 50,000-position dataset is in `data/lichess-50k/`. Training does **not**
automatically replace the competition champion.

If this folder is moved to another computer, run `setup.ps1` to create `.venv` first.
The scripts use that environment when present. Alternatively run the Python modules
directly using Python 3.12 with `requirements-dev.txt` installed. No installation code
is included in the competition zip.

## What is included

- `submission.zip`: selected classical competition-shaped runtime; not uploaded.
- `agent.py`, `engine/`: original search and evaluation source.
- `nn/`, `training/`: NumPy learning framework, training, export, data and offline tools.
- `models/value.npz`: first self-trained value model, experimental and not in the default zip.
- `champions/`: preserved classical build and package.
- `docs/USER_GUIDE.md`: explanations and practical commands.
- `docs/TECHNICAL_DISCLOSURE.md`: provenance, results and package audit.
- `docs/RESULTS.md`: measured experiments and outstanding limitations.

The official harness and baselines are preserved under the starter's MIT licence.
They are development tools and are excluded from the submission. Organiser validation
on the real Linux container is still required before any competition acceptance claim.

<!-- CURRICULUM_SESSION_START -->
## Phase curriculum pilot

The controlled phase-coverage experiment is complete. Do not adopt this pilot as an improvement; it showed a regression in the small comparison. See `docs/CARLSEN_CURRICULUM_RESULTS.md` for the 32-game comparison, validation counts, scope and reproduction steps. Candidate and equal-compute control are preserved separately; neither automatically replaces the baseline.
<!-- CURRICULUM_SESSION_END -->
