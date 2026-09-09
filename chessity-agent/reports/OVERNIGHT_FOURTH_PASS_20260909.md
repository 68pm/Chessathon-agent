# Overnight fourth checkpoint —9September2026

**v1.53 remains the selected competition upload.** No v1.54 has been assigned.
The six-game neural countercheck screen completed, but it did not justify replacing
the retained release. A new classical integration is being checked separately;
its unfinished work is excluded from this report.

## Exact playing results

All games below use120s+0.5s. W/D/L is from the candidate's perspective.

| Candidate and setting | W | D | L | Important qualification |
|---|---:|---:|---:|---|
| Exact v1.53, latest E55 pair vs nominal2400 |1|0|1|Two games only|
| Exact v1.53, latest E55 pair vs nominal2600 |0|1|1|No2600win|
| Exact v1.53, all saved rated2400 games |1|1|2|Includes the latest pair|
| Exact v1.53, all saved rated2600 games |0|1|3|Includes the latest pair|
| Countercheck-leaf-01 vs compiler-repaired v1.53 control |2|1|1|Both wins with White; Black0W1D1L|
| Countercheck-leaf-01 vs nominal2400 |0|0|2|One played checkmate loss; one startup failure|

The control is a distinct compiler-repaired build, not the exact selected ZIP.
Do not pool its games, or the experimental candidate's games, into v1.53's record.
The failed startup is retained in the results: the Black agent exceeded its90s
initialization allowance. Available memory was about2.1GB before and after that
game; these data do not establish insufficient RAM as the cause. No moves were
played by that agent in the failed game.

The highest clean rated-setting win remains **one win at nominal2400** by exact
v1.53. There is no2600,2800or3000win in these results and no calibrated Elo estimate.
Local weakened-engine settings and a few games cannot establish a tournament
rating. This report does not assert a newly checked live dashboard rating or
which ZIP is currently uploaded there.

## What the new games taught us

All six experimental games were reviewed, covering247 played candidate moves:
123 received positive move feedback and22 negative feedback. Other moves were
neutral or uncertain. The zero-move startup loss generated no new move examples;
its checkpoint replayed existing examples. Game results and opponent ratings
did not determine individual move rewards. Playing candidates stayed frozen;
postgame policy checkpoints remain experimental.

The latest2400loss contained a clear data gap. The original review marked33.Bxc4
as a major mistake but could not choose one policy target because the two
Stockfish budgets proposed different alternatives. Individually checking the
alternatives found33.Qb4 at-35/0cp, versus Bxc4 at-290/-272cp. That gave a supported
alternative without inventing a unique best move. Eight continuation positions
were independently evaluated; five passed the fixed value-label stability rules.

The separate D65 Black35.Qxd4 pawn capture remains a serious tactical weakness.
Qd6 scored111/167cp, but narrowly failed the declared50cp safe-alternative gate
against the previously recorded unrestricted references. That failure remains.
Deeper, independent320k/1.28M endpoint analysis confirmed that two Qxd4
continuations were losing: -719/-752cp and-800/-879cp. Parent move rewards were
never copied onto these descendant positions.

## Training and engineering outcomes

One calibrated fit changed only64 output weights while retaining the781x64
encoder. It learned the exposed D65 positions but transferred poorly:

| Position set | Count | Old runtime MAE,cp | New MAE,cp |
|---|---:|---:|---:|
| Exposed D65 development training |33|291.508|179.048|
| Broad active middlegame validation |999|223.966|234.764|
| C09/D28 grouped endpoint holdout |22|238.388|249.858|

**The fit was rejected.** The output was frozen before the22 new holdout labels
were produced. Those games' roots had already been seen, so this remains local
development validation, not independent playing-strength evidence. Earlier
frozen D65 validation data were explicitly reassigned to training only in this
new recipe; the old records and failed gates were preserved.

A compiler-only neural experiment lowered observed startup to58.976s and
reproduced26 saved fixed-depth decisions. Its104 timed probes nevertheless failed
the tactical gate because of the D65 pawn-capture weakness. It was not sent into
another match screen. The first compiler trial's request-field collision was
caught before any search; that failed preflight is also retained.

The remaining engineering direction is to preserve the measured classical
evaluation speed gain and useful defensive counterchecks while avoiding the
neural search overhead. Only a genuinely changed candidate that passes short
checks may replace v1.53. No long consistency study is being run.

## Upload and evidence

Selected archive: `latest/chessity-agent.zip`, identical to the v1.53 archive.
SHA256: `5747acec37da25ea79704e49d19e45bf23bd2af5842a14eaf66bf6ecf2791315`.
All54 numbered archives are retained without byte changes. Runtime inference
remains read-only, with no Stockfish, networking or training inside the upload.

The accompanying `evidence/overnight-fourth-pass-20260909/` contains completed
trial states, game PGNs, feedback records, frozen plans and the calibrated-fit
results. Source and tests are under `development/`. Experimental model files
are not presented as competition-ready releases. The07:20BST report and06:40BST
cutoff remain in force.
