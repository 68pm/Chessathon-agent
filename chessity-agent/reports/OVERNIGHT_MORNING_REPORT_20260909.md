# Chessity morning report — 9 September 2026

**Recommended upload: chessity-agent v1.42.** The exact archived v1.42 beat the
previously selected v1.53 by **3 wins, 1 draw, 0 losses** in the completed short
comparison. Both colours and two opening groups were used. All three wins were
checkmates, and neither side had a startup, clock, crash or illegal-move failure.

The recommendation returns to an existing version. Its code and weights are
unchanged; no new neural model or v1.54 is being claimed. This small comparison
supports the practical selection, but it does not establish universal superiority.
v1.53 and all 54 numbered archives are preserved.

Download the recommended ZIP from `latest/chessity-agent.zip`, or use the exact
`versions/v1.42/chessity-agent-v1.42.zip` archive. Both contain the same bytes.

SHA256: `114c1688a63d4039d7965670fcab0891bec24d4835dacafa8698e22d0c01f48b`.

## Results and rating limits

All rows use **120 seconds + 0.5 seconds per move**. Wins/draws/losses are from
the named agent's perspective. Historical rated screens and today's comparison
are separate samples; the older rated screen used two concurrent games, while
the overnight comparison ran serially.

| Agent and opponent | Wins | Draws | Losses | Scope |
|---|---:|---:|---:|---|
| v1.42 vs exact v1.53 | 3 | 1 | 0 | New four-game C09/D28 comparison |
| v1.42 vs nominal 2400 | 2 | 0 | 2 | Historical cycle 03, 7 September |
| v1.42 vs nominal 2600 | 1 | 2 | 1 | Historical cycle 03, 7 September |
| Exact v1.53 vs nominal 2400 | 1 | 1 | 2 | Its two earlier E90/E55 pairs |
| Exact v1.53 vs nominal 2600 | 0 | 1 | 3 | Its two earlier E90/E55 pairs |

In the new comparison, v1.42 scored **2W/0D/0L with White** and **1W/1D/0L with
Black**. C09 produced two wins; D28 produced a win and a draw. The complete game
record and feedback were audited before changing the recommended download.

The highest clean rated-setting victory verified for the recommended build is
**one checkmate win over Stockfish configured at nominal 2600**, from its earlier
cycle 03 screen. There is no verified 2800 or 3000 win in the reviewed archive.
The v1.49 archive's opponent-flag win at 2600 is excluded from clean strength wins.

**A calibrated Elo rating has not been established.** These weakened-engine
settings and small samples are not the competition's rating scale. The latest
four-game comparison finished at 06:17 BST. The next rated pair required a full
25-minute allowance before the fixed 06:40 cutoff, so no new rated pair started.
The historical 2400/2600 scores above are not new overnight tests.

## What changed and what stayed experimental

The work followed search efficiency, defensive move selection, independently
labelled position values, and targeted game preparation. The measured pawn-mask
evaluation change achieved about **1.53x aggregate CPU speed** in its fixed-node
test, with exact evaluation and decision parity there. Its timed tactical gate
still failed, so that speed result alone did not earn a release.

The neural countercheck candidate completed **2W/1D/1L** against a separate
compiler-repaired v1.53 control, then **0W/0D/2L at nominal 2400**. One rated loss
was a played checkmate; the other was a 90-second startup failure with about
2.1GB available memory. That observation does not establish insufficient RAM as
the cause. All six outcomes were retained and reviewed. The candidate was rejected.

A later classical integration started in 48.6 seconds but failed its tactical
gate. Inspection found that an interrupted root search discarded completed child
results and could fall back to the first generated legal move. A bounded seed
search and completed-child fallback fixed that behaviour, passed 22 tests, and
improved average probe regret from 154.2/173.8cp to 139.0/154.2cp at the two teacher
budgets. It still introduced a major mistake in another position and was rejected.
These useful code changes remain isolated for further development.

The single calibrated value-head fit changed only 64 output weights. It used
independent descendant labels, including deeper checks of two losing pawn-grab
continuations. It improved its exposed training positions but worsened validation:

| Position set | Count | Old runtime error, cp | New error, cp |
|---|---:|---:|---:|
| Exposed D65 development training | 33 | 291.508 | 179.048 |
| Broad active middlegame validation | 999 | 223.966 | 234.764 |
| C09/D28 endpoint holdout | 22 | 238.388 | 249.858 |

That fit was rejected. The output weights were frozen before the 22 new holdout
positions were labelled. Previously observed game groups are development data;
neither this fit nor replayed positions count as independent strength evidence.

## Learning from wins, losses and the draw

The four new v1.42 games contain **206 reviewed candidate moves: 120 positive
move labels and 17 negative labels**, with the remainder neutral or uncertain.
Stockfish evaluation, rather than game outcome or opponent rating, determined
move rewards. Each game produced a separate experimental policy checkpoint.
The playing version's weights remained frozen throughout the comparison.

A separate review covered all **204 v1.53 moves: 88 positive and 26 negative
labels**. Both perspectives therefore cover all **410 played moves** in the same
four games; these are not eight extra games. Its experimental policy fit used
**105 examples and 15 updates**. Training reduced its own objective, but that
checkpoint has not passed playing tests and is absent from the recommended ZIP.

The drawn D28 game exposed a defensive mistake: **32...Qa1+** evaluated at
-379/-442cp, while **32...b2** held an equal 0/0cp evaluation at the two budgets.
This is a concrete defence target. The available analysis does not show that
v1.42 had a win at that point. Another winning game still contained a major
28.Rdc1 mistake, so winning games also supply useful corrections.

A fixed follow-up curriculum independently evaluated **58 descendant
positions**, of which **54 passed the value-label stability rules**. The
prepared set contains 39 middlegame, 6 opening and 13 endgame positions. These
labels are saved for future value training; no additional value fit was run.
Each position received its own Stockfish value; parent move rewards were not
copied onto descendants. These C09/D28 groups were already exposed development
data and must not be described as a fresh strength holdout. Two earlier adapter
attempts were preserved: a Windows path failure before analysis, then an empty
target-field schema collision after the first endpoint analysis. The corrected
attempt reused cached analyses. No additional broad GM download was needed.

## Upload checks and remaining limits

The selected v1.42 ZIP passed a fresh strict read-only check: two legal move calls,
optional Alien preparation and elementary endgame tables verified, and file
creation/deletion, directory creation and rename attempts blocked. Inference
uses no network, subprocess or training. Cold initialization took **82.2 seconds**
under the 90-second limit; the narrow margin is a remaining reliability concern.

The local download metadata previously said v1.41 while its ZIP was v1.53. The
old metadata was backed up and corrected. The morning selection now aligns the
download ZIP and its metadata with v1.42; numbered archive bytes are unchanged.

The browser connection failed before it could read the live dashboard, including
after one reset. **The current competition rating and currently uploaded version
remain unverified.** No competition submission or repository permission change
was performed. The 07:20 report distinguishes local evidence from live rankings.
