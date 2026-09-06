# Carlsen curriculum: controlled pilot

**Recommendation: Do not adopt this pilot as an improvement; it showed a regression in the small comparison.** The experimental candidate is `candidates/carlsen-curriculum-v1.zip`; the equal-compute control is `candidates/carlsen-curriculum-control-v1.zip`. Neither replaces the prior combined packages or the selected classical submission.

The user supplied `docs/CARLSEN_CURRICULUM_PROMPT.md`. This implementation applies its smallest compatible data experiment: better phase coverage with the existing move-policy architecture and base loss. It does not claim to implement every theme in the prose or reproduce Carlsen's thought process.

## What changed

Both recipes start from `classical-witty-magnus-v1`, use 8,192 real training positions (half from each player), share 1,024 validation positions, run three epochs at learning rate 0.0001 and use the same seed and batch count. Common positions share the exact encoded features and negative alternatives. The ordinary control samples without phase balancing. The curriculum combines 50% ordinary sampling with 50% phase-balanced sampling. Checkpoints use validation cross-entropy; the previous final test set is excluded from this experiment.

A separate 1,024-position pipeline pilot checked legal labels, finite features/loss/gradients and whole-game separation before either recipe. Its temporary model was discarded. Both player datasets and all their outcomes/colours remain represented; source URLs, PGN checksums, player side, time control and time class are retained. Whole-game splits and exact FEN deduplication are inherited from the audited source pool. Related positions may remain across splits.

Phase categories use remaining material, queen count and minors on initial back-rank squares, with overlapping tags. They are heuristic categories, not expert plan annotations or move-number cutoffs. Mechanically checked tags include checks, captures, quiet moves, king moves, castling, promotions, queen captures, open files and passed pawns. These facts categorise examples; they do not assert that an action is good and never add rewards. Prophylaxis, exploitable weaknesses, fortresses and multi-step strategic plans have not been automatically labelled or learned as verified concepts.

**Runtime limit:** the classical search and all runtime code are unchanged. Its neural preference remains disabled in check, strongly imbalanced positions and material phase <=0.20. Thus this pilot's late-endgame neural learning does not affect those production decisions. FEN policy inputs lack full repetition history; full histories remain recoverable from the referenced source PGNs, while runtime search keeps its existing draw handling. No external teacher labels, tablebases, new value head or permanent move bonuses were introduced.

## Phase coverage

| Primary phase | Control train | Curriculum train | Common validation |
|---|---:|---:|---:|
| opening | 1118 | 1363 | 165 |
| early_middlegame | 1870 | 1771 | 238 |
| middlegame | 2185 | 1920 | 227 |
| transition | 1730 | 1659 | 214 |
| endgame | 1289 | 1479 | 180 |

## Development-set move agreement

These are raw policy choices on the common validation set, used for development—not a fresh final test or a measure of tactical correctness.

| Phase | Baseline top 1 | Control top 1 | Curriculum top 1 |
|---|---:|---:|---:|
| opening | 40.6% | 39.4% | 42.4% |
| early_middlegame | 36.6% | 35.7% | 36.6% |
| middlegame | 34.8% | 33.9% | 35.2% |
| transition | 36.9% | 36.9% | 36.9% |
| endgame | 46.1% | 46.1% | 45.6% |

## Fixed match results

| Opponent | W | D | L |
|---|---:|---:|---:|
| control:None | 2 | 4 | 2 |
| baseline:None | 1 | 4 | 3 |
| madchess:1500 | 2 | 0 | 2 |
| madchess:1700 | 1 | 1 | 2 |
| madchess:1900 | 0 | 0 | 4 |
| stockfish:1700 | 0 | 3 | 1 |

All 32 games used 30+0.3, both colours, fixed openings and at most two simultaneous games. There were eight games against the control, eight against the frozen Magnus/Witty baseline, and four each at MadChess 1500/1700/1900 and Stockfish 1700. The schedule was fixed before outcomes. All PGNs replayed correctly. Terminations: `{"threefold_repetition": 12, "checkmate": 20}`. Highest checkmate wins: `{"madchess": 1700, "stockfish": null}`. These are opponent settings, not an Elo rating for the candidate.

The direct comparisons contain only four colour pairs each. Their descriptive pair standard errors are `{"control": {"score": 0.5, "pair_standard_error": 0.10206207261596575, "colour_pairs": 4, "caution": "Descriptive small-sample standard error; no calibrated Elo or established improvement."}, "baseline": {"score": 0.375, "pair_standard_error": 0.07216878364870322, "colour_pairs": 4, "caution": "Descriptive small-sample standard error; no calibrated Elo or established improvement."}}`; the sample is too small to establish a reliable strength gain.

## Concrete checks, speed and limits

Verified small counterexamples cover taking an immediate mate instead of continuing development, answering check in a queenless ending, avoiding queen-promotion stalemate, and preserving valid draw outcomes. A rook promotion retains mating material where a queen immediately stalemates; non-promotion moves that avoid immediate draw are also accepted, so this is not a proof of eventual conversion. Colour mirrors give 14 cases per model. Passed: `{"baseline": 14, "control": 14, "curriculum": 14}`. These are known diagnostic positions, not evidence of opposition, triangulation, rook-endgame or fortress mastery. Full FENs and chosen moves are in the evidence file. Lost match PGNs remain available as concrete failure records; no unverified strategic explanation is assigned to a loss.

Raw policy inference timings on the same 256 validation positions, including feature encoding (milliseconds): `{"baseline": {"positions": 256, "median_ms": 0.9088000006158836, "p95_ms": 1.7703750054351985, "max_ms": 2.506300006643869}, "control": {"positions": 256, "median_ms": 0.9727500000735745, "p95_ms": 1.8902250048995484, "max_ms": 2.734000008786097}, "curriculum": {"positions": 256, "median_ms": 1.0455499941599555, "p95_ms": 2.2236999902816024, "max_ms": 3.5595000081229955}}`. Architecture and parameter count remain unchanged. Each extracted ZIP passed 130 legal-move calls and active-policy checks with no writes, networking or subprocesses. Unit checks total 54. Organiser Linux validation remains separate.

Training loops used 11.97 seconds in total, excluding data preparation, shared feature encoding, diagnostics and matches. Best checkpoints and optimiser states are in `runs/carlsen-curriculum-20260906/training/`. The source and commands are retained in `training/chess_curriculum.py`, `training/curriculum_pilot.py`, `scripts/curriculum_session.py` and `configs/carlsen-curriculum-pilot.json`; use fresh output directories to preserve evidence.

Evidence: `docs/evidence/carlsen-curriculum-20260906-session.json`, `docs/evidence/carlsen-curriculum-20260906-games.json`, and four opponent-family PGNs. Training sources are the already authorised, downloaded public player histories. [Maia research](https://www.maiachess.com/) distinguishes human move imitation from maximising strength; this pilot keeps that distinction explicit.

## Reproduce the data and training

From the project root with its Python environment (use fresh output paths):

```powershell
python -m training.chess_curriculum --out runs/curriculum-repeat/data
python -m training.curriculum_pilot --data runs/curriculum-repeat/data --out runs/curriculum-repeat/training
python -m scripts.curriculum_diagnostics --training runs/curriculum-repeat/training --out runs/curriculum-repeat/diagnostics.json
```

Package commands and the fixed benchmark are recorded in `scripts/curriculum_session.py`.
Its dated paths deliberately reject overwriting this experiment. To repeat matches,
configure a fresh run path and new frozen candidate folders in a copy of the controller.
Shared feature caches may be rebuilt from `training/union.jsonl` using
`training.player_policy.build` with seed 20260907. A cache cleanup manifest records
the original checksum; data, checkpoints and match evidence remain preserved.
