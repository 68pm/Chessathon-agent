# Chessity agent: final combination and competition-clock test

**Best observed comparison score: `magnus`, published as chessity-agent v1.14.** The exact selected competition ZIP is `chessity-agent.zip` in the parent outputs folder. SHA-256: `6d287209c28bba520a21ef49261af99543a167fb192ce15513102c883c503a56`. Selection followed the predeclared score/tie rule; this small local test does not prove that it is the strongest possible agent.

## What was combined

The two new fusion candidates combine the existing original 300k-position value model (775–128–32–1) and the newer move-policy model (935–64–32–1) with the original classical search. The policy retains Witty/Magnus imitation and the verified puzzle pilot's ordinary phase-coverage, puzzle and failure-replay training. These are two compatible learned components used by one agent; incompatible weight matrices were not averaged or presented as a single newly trained architecture. Some accumulated data was used for validation/testing rather than training; raw player histories were sampled rather than every move being fitted.

`fusion-hybrid` evaluates search leaves using 80% classical and 20% learned value, with a bounded 10cp policy preference. `fusion-root` retains classical node evaluation and adds at most 5cp from the learned child-position value to the 10cp player/puzzle preference, under the existing root guards. Child values are negated back to the root mover's perspective; terminal mate/draw outcomes are handled explicitly. The latter avoids neural evaluation at every search leaf. Both retain the optional 15cp Alien opening hint. The engine can decline the sacrifice. Speculative aggression never receives an unconditional training reward.

The failed curriculum checkpoint was preserved rather than averaged into a new model. Its useful phase-sampling data had already been incorporated into the puzzle experiment. Historical baselines and all experimental variants remain versioned. If a preserved baseline tops the final comparison, it is selected on the evidence rather than automatically replacing it with the newest file.

## Fixed comparison at 120+0.5

The user confirmed **120 seconds per side plus 0.5 seconds per move**. All 54 games in this final session used that clock, a 600-ply cap, both colours, and at most two simultaneous games. The earlier 30+0.3 experiments remain historical evidence and did not substitute for these fresh games.

Six agents played one colour-reversed opening pair per opponent pairing: 30 games total and ten per agent. Pair openings and the exact tie preference were frozen before outcomes in `configs/final-fusion.json`. The highest total selected the candidate for the separate rated tests. The score advantage is provisional; ten games per agent is a small screening sample.

| Agent | W | D | L | Points / 10 |
|---|---:|---:|---:|---:|
| magnus | 5 | 3 | 2 | 6.5 |
| classical | 3 | 6 | 1 | 6.0 |
| value-300k | 4 | 3 | 3 | 5.5 |
| fusion-root | 2 | 4 | 4 | 4.0 |
| fusion-hybrid | 2 | 4 | 4 | 4.0 |
| puzzle | 2 | 4 | 4 | 4.0 |

## Fresh rated opponents

| Stockfish setting | W | D | L | Games |
|---|---:|---:|---:|---:|
| 2000 | 2 | 1 | 9 | 12 |
| 2200 | 1 | 4 | 7 | 12 |

Highest opponent setting defeated in these final tests: **2200**. The opponent was Stockfish 19 with `UCI_LimitStrength=true`, the stated `UCI_Elo`, one thread, 64MB hash and 20ms move overhead. It is a locally handicapped engine, not a verified human or Chess.com bot rating. The official [Stockfish UCI documentation](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-Protocol-and-Stockfish-Commands.html) describes these options. No independent Elo rating is inferred from a highest individual win.

Each level used six opening pairs, with colours reversed. Pair standard errors were `{"2000": 0.1003466214899358, "2200": 0.09128709291752768}`; a zero empirical standard error from identical outcomes does not mean zero uncertainty. All recorded PGNs were legally replayed and the result, opening, time-control and frozen-file checks passed. Terminations: `{"2000": {"checkmate": 11, "threefold_repetition": 1}, "2200": {"threefold_repetition": 4, "checkmate": 8}}`.

## Read-only runtime and resources

The new entrypoints disable bytecode caching. Package probes reject file creation, deletion, directory creation and renaming, plus other filesystem mutation events, networking and subprocesses. The selected ZIP passed again at a 120,000ms remaining-clock input. Import time was 1067.09ms; observed peak working set was 36220928 bytes. These are local measurements, separate from organiser Linux validation. Training code writes checkpoints outside the runtime package. Runtime transposition/history updates occur only in memory.

The agent ZIP contains readable Python and the selected original trained weights. No external engine implementation, executable, teacher weights, downloaded game archive or teacher evaluation lookup database is included. The competition permits training a team's own network on engine-labelled positions; see its [documentation](https://aichessathon.com/docs). Authorship and data provenance are described in the earlier player and puzzle reports. All source was developed with AI coding assistance.

## Reproduction and evidence

`scripts/final_fusion_session.py` records the exact build, package, test, validation, comparison and rated-test commands. `configs/final-fusion.json` records the final clock, candidates, data-model paths, bounded fusion constants and selection rule. Dated paths refuse overwriting evidence; use new output paths for another experiment. Opponent randomisation and wall-clock search timing can vary across runs.

`docs/evidence/final-fusion-20260906-session.json`, the comparison/rated JSONs and PGNs preserve the results. `runs/final-fusion-20260906` contains per-game records, clocks for rated games, package probes, source hashes and all controller logs. The original value/policy training datasets and checkpoints remain in the local project. No competition upload was performed by these tests; the user receives the verified ZIP to submit.
