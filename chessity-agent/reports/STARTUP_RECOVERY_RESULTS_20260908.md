# Chessity v1.51: startup revision and four completed games

**Recommended upload: v1.51**, a practical startup revision of v1.41.
Its playing search, evaluation, policy weights, optional Alien Gambit and
elementary endgame tables are unchanged. This is not new neural training or a
demonstrated increase in chess strength. The previous v1.41 ZIP remains available
as a fallback. v1.50 preserves the intermediate startup build that failed its
instrumented protocol check and is not recommended.

The ready signal now follows completion of the one-depth root compilation even
if earlier setup consumed the old internal deadline. Compiler diagnostics are
plain text, avoiding the Windows console-color initialization path. The external
90-second initialization limit is unchanged. Focused startup checks passed
(three readiness cases and two plain-diagnostic cases). Strict read-only checking
passed: initialization 61.531 seconds, two legal calls, maximum move 3.487 seconds,
peak working set 232,681,472 bytes. No filesystem mutations, network or subprocess
access are used by the submission.

## Completed practical games

Exactly four serial games, 120 seconds + 0.5 seconds, from the predeclared C58
start with both colours at each nominal Stockfish setting. All legal-move, clock,
source and outcome audits passed. No extra games were added after seeing results.

| Opponent setting | Wins | Draws | Losses | Candidate runtime failures |
|---|---:|---:|---:|---:|
| Stockfish nominal 2800 | 0 | 1 | 1 | 0 |
| Stockfish nominal 3000 | 0 | 1 | 1 | 0 |

At each level White lost by checkmate and Black drew by threefold repetition.
There were no flag results. Each level has just one opening pair; the runner's
degenerate single-pair bootstrap interval is not useful uncertainty evidence.
These handicap settings are not a calibrated rating. This build has no verified
win against these levels and has not established consistent 2600 strength.

## Selection and limitations

The [rule declared before these games](STARTUP_RECOVERY_GAMES_20260908.md) allowed
a startup reliability recommendation after four audited games without candidate
initialization, crash, illegal-move or flag failures. It also required the playing
code to remain identical outside startup. Both conditions passed. Release checks
confirm only agent.py and the driver's warmup differ from v1.41, with AST parity
elsewhere and byte-identical models, evaluation, core search and tables.

The canonical harness request passed: initialization 50.292 seconds, legal Bb5
response 5.020 seconds, no stderr. The separate instrumented request still crashed
after 35.554 seconds. That failure and v1.50's failed 90.298-second request remain
in the evidence. Four successful games do not prove universal startup reliability
or establish the cause of the instrumentation failure. No cause of Codex app
crashes is inferred. Previous zero-move overnight losses are preserved separately
in the [historical morning report](OVERNIGHT_REPORT_20260908.md).

## What the mistakes suggest next

The offline teacher examined 178 own moves and verified three finite errors of
at least 200 centipawns at both 80,000 and 320,000 nodes. All three occurred in the
operational middlegame category; both losses eventually ended in the endgame.
The finite screen can miss earlier causes, and mate-scored positions stay separate.

| Game | Played | Verified alternative | Regret at the two budgets |
|---|---|---|---|
| White vs 2800, move 37 | Kf1 | Kg2 | 674 / 734 cp |
| Black vs 2800, move 16 | ...f4 | ...e4 | 259 / 270 cp |
| White vs 3000, move 40 | Rc8 | Nd1 | 283 / 284 cp |

The king move is a useful quiet-defence target. The pawn move missed an advantage
in a game eventually drawn. The rook-move position was already losing, so it is
not labelled the cause of that loss. The saved phase review uses no new teacher
nodes and queues four review references, not automatically accepted new labels.

Engine work remains first: test one bounded useful-depth improvement against the
working startup baseline. Learning comes second: the previous replay loss failed
against its matched control, and many requested corrections exceeded its allowed
125 cp contribution; use a compatible objective before another fit. Targeted data
comes third: these verified defensive and conversion mistakes are sufficient for
the next diagnosis. No broad download or long consistency study is needed.

## Downloads and historical results

Selected ZIP SHA256: `f23376c7c33ad28ccb2276c16b8b242c84e34492e7ef3910691e4cb9b58a79e2`.
ZIP size: 272,625 bytes. All 52 numbered versions through v1.51 are preserved.
No live competition submission or repository permission changes were made.

v1.41's separate later short check scored 0W/0D/2L at nominal2400 and 1W/0D/1L
at nominal2600, all checkmates. Nominal2600 is its highest verified played win.
Those old wins are not attributed to v1.51. Its earlier confirmation and inferred
competition rounds54–56 are preserved in the
[previous selection report](IMPROVEMENT_RESULTS_BEFORE_STARTUP_20260908.md).

[Selection provenance](evidence/startup-recovery-20260908/selection.json) ·
[Full four-game results](evidence/startup-recovery-20260908/startup-recovery-games-01/rated-compiled-startup-plain-v1/results.json) ·
[Phase diagnosis](evidence/startup-recovery-20260908/startup-recovery-games-controller/phase.json) ·
[Evidence manifest](evidence/startup-recovery-20260908/manifest.json)
