# Three-phase progress snapshot

Snapshot UTC: 2026-09-06T22:53:32.149107+00:00. Improvement work remains in progress.

**Recommended competition upload: v1.14.** The new v1.24 is experimental, pending full comparison and final rated tests.

## Completed baseline at 120+0.5

| Stockfish setting | Wins | Draws | Losses |
|---|---:|---:|---:|
| 2200 | 1 | 0 | 3 |
| 2400 | 1 | 1 | 2 |
| 2600 | 0 | 0 | 4 |

The baseline's highest individual winning setting in this fresh set is 2400. These are nominal engine settings, not a measured Chess.com/FIDE rating. All 12 baseline PGNs, clocks, increments, results and frozen source files passed replay audits.

## New candidate and data

The supplied pack's 1,838 games and 107,439 observations were legally reconstructed. The phase pilot independently verified 384 positions (192 diagnostic train, 96 validation, 96 test) at 80k/320k nodes, quarantining 57 unstable or unsuitable candidates. These are finite teacher estimates, not tablebase proofs. No new neural weights were fitted; the first experiment improves the project's search implementation.

The full local suite passed 83 tests. The candidate also passed read-only smoke checks. It uses targeted quiescence move generation and principal-variation search; it retains the classical evaluator and locally trained v1.14 policy.

On the 96 validation positions, the baseline/candidate accepted 72/71 moves at a 4000ms remaining clock, 71/69 at 800ms, and 71/71 at 2000 nodes. Each had five verified 200cp errors in these modes. These mixed results do not establish an improvement. Modes reuse the same positions; timing reflects local host load.

At this snapshot, the candidate's development match had completed 3/8 games: 3 wins, 0 draws and 0 losses. This partial result does not promote the candidate. No new candidate win against 2600 is claimed.

Next: finish the first comparison, assess the bounded second search experiment if warranted, then freeze a challenger for fresh confirmation and fixed 2200/2400/2600 tests plus endgame conversion drills. The schedule will not be extended simply to obtain a 2600 win. The tested agent weights remain fixed during benchmark games.

Downloaded source histories, historical book texts and external engine executables are not included in this public update. No repository write permissions were granted. No competition upload was performed.
