# Chessathon-agent

**Recommended upload: [chessity-agent v1.42](chessity-agent/latest/chessity-agent.zip).**

The exact archived v1.42 scored **3 wins, 1 draw, 0 losses against exact v1.53**
in the completed 9 September comparison at **120s + 0.5s**. Both colours were
used, with no operational failures. This selects an existing build with unchanged
code and weights; no new neural model or v1.54 is claimed.

| v1.42 opponent | Wins | Draws | Losses | Evidence |
|---|---:|---:|---:|---|
| Exact v1.53 | 3 | 1 | 0 | New four-game comparison |
| Stockfish nominal 2400 | 2 | 0 | 2 | Historical 7 September screen |
| Stockfish nominal 2600 | 1 | 2 | 1 | Historical 7 September screen |

The highest verified clean setting win for this upload is **2600 once**. No
verified 2800/3000 win or calibrated Elo has been established. No new rated pair
ran this morning. These small development samples do not establish a live
competition rating or universal superiority.

[Morning report](chessity-agent/reports/OVERNIGHT_MORNING_REPORT_20260909.md) ·
[All 54 versions in order](chessity-agent/README.md) ·
[Current results](chessity-agent/reports/IMPROVEMENT_RESULTS.md)

All 410 moves in the four comparison games were reviewed from both perspectives.
Independent descendant labelling produced 58 positions, 54 eligible for future
value training. Experimental policy and value changes remain separate from the
playing ZIP unless they pass short practical tests.

The recommended ZIP passed strict read-only checks. Its SHA256 is
`114c1688a63d4039d7965670fcab0891bec24d4835dacafa8698e22d0c01f48b`.
Cold initialization took 82.2 seconds against a 90-second limit, leaving limited
startup margin. No live competition upload or repository permission change was
performed; the current site rating and uploaded version remain unverified.

[Archived pre-selection repository overview and earlier results](chessity-agent/reports/ARCHIVED_REPOSITORY_README_BEFORE_20260909.md)
