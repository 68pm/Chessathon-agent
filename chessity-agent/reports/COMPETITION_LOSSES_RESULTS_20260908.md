# Recent competition losses, draw and persistent engine problems

Rounds 61–69 contain **4 wins, 1 draw and 4 losses**. The user believes the upload
was v1.41, but this is unconfirmed: public games expose no submission hash.
These results must not be attributed to v1.53. All nine original PGNs, clocks,
source URLs/hashes and website reviews are retained. All eight decisive games
ended in checkmate; round 68 ended by threefold repetition, not a timeout.

The public Stockfish 16 depth 16 review screened the games. Fourteen selected
positions from the four losses and draw then received independent Stockfish 19
analysis at 80k and 320k node limits with the actual history. These are targeted
development examples, not a complete independent review of every move or Elo test.

## What went wrong

| Game | Verified problem | Better continuation and implication |
|---|---|---|
| Round 61 vs TheROOK, loss | Middlegame 26.Qe3 allows ...f4 and a forcing attack. Later 50.Rxa6 abandons a drawing defense. | 26.f3 limits the damage but the position is already worse; at 50, Re6+ retains a perpetual while Rxa6 allows ...h2. Stop treating pawn captures as safe when checking threats or promotion dominate. |
| Round 62 vs Zagreus5.0, loss | 27...Bd7 worsens defense; 29...f6 turns a roughly equal position into a large disadvantage. | Qe5 at 27; Kh8 at 29. After ...f6, e5 opens tactics culminating in Nf6+. Both versions still struggle at the move27 position. |
| Round 63 vs Alpha Knights, loss | 22.Qc6 overlooks ...Bf3 followed by ...Bxc6, losing the queen. | f3 closes the immediate threat. v1.53 finds this defense in the one-second replay. |
| Round 66 vs Magnus CarlSON, loss | 28.Bb2 misses the necessary exchange on e3; both versions later choose a pawn grab permitting forced mate. | 28.Bxe3 Rxe3+ keeps the position near equal. At 32, both choose Rxb7 in replay; ...Qe3+ starts the mating attack. The actual 32.Qd3 is also bad, with budget-sensitive severity. |
| Round 68 vs berserker, draw | 80.Ra1 permits the actual threefold repetition after ...Kf6. Both versions repeat it. | Rf1/Re1 retains about+2 pawns at both budgets. The plan includes active rook play and Kg4. This is a squandered advantage, not proof of a forced win. |

The earlier draw-game 51.Ke3 is **not established as a major mistake**: the larger
search puts it only 4cp behind the alternative. Do not train the agent to reject
all draws or chase a nominal advantage without sound continuation.

## Old and newer engine comparison

Exact archived v1.41 and selected v1.53 each received fourteen one-second probes,
policy disabled, fresh tables and full game history. Initialization 66.246s and
71.540s; every move legal, board restored and measured clock bound satisfied.
These probes differ from the actual competition's per-move time allocation.

Across thirteen commonly finite positions, paired ≥200cp errors fell **7 to 4**.
Mean regret fell **350/339cp to186/179cp** at 80k/320k. Both versions additionally
choose a forced-mate losing move in the fourteenth position; it is excluded
from finite averages and retained separately. This is improvement on an exposed
development set, not evidence of a particular playing rating.

Table cells show the selected move and regret at 80k/320k, in centipawns.

| Round / actual move | Stage | Teacher320k | v1.41 choice (regret) | v1.53 choice (regret) |
|---|---|---|---|---|
| 61 19.Bg5 | middlegame | b5 | Bg5 (63/114) | Bg5 (63/114) |
| 61 26.Qe3 | middlegame | f3 | Qe3 (866/717) | Qe3 (866/717) |
| 61 50.Rxa6 | endgame | Re6+ | Rxa6 (715/715) | Re6+ (0/0) |
| 62 19...Nxd4 | middlegame | Qxd4 | Nxd4 (90/82) | Nxd4 (90/82) |
| 62 27...Bd7 | middlegame | Qe5 | a5 (204/207) | Ne2 (395/364) |
| 62 29...f6 | middlegame | Kh8 | b5 (564/572) | Kh8 (0/0) |
| 63 21.Be3 | middlegame | f3 | Rfe1 (92/85) | f3 (0/0) |
| 63 22.Qc6 | middlegame | f3 | Qc6 (771/777) | f3 (0/0) |
| 66 25.a4 | middlegame | Qd3 | a4 (137/126) | c4 (18/33) |
| 66 28.Bb2 | middlegame | Bxe3 | Bb2 (694/719) | Ba3 (632/720) |
| 66 32.Qd3 | middlegame | Qe4 | Rxb7 (mate/mate) | Rxb7 (mate/mate) |
| 68 27.dxc4 | middlegame | Nxc4 | dxc4 (87/85) | dxc4 (87/85) |
| 68 51.Ke3 | endgame | Kg4 | Ke3 (60/4) | Ke3 (60/4) |
| 68 80.Ra1 | endgame | Re1 | Ra1 (209/204) | Ra1 (209/204) |

## Fixes and learning use

1. **Engine first:** improve useful search depth while preserving forcing-check
coverage, defensive exchanges and promotion threats. A separately predeclared
root scout integration tests this on v1.53. Its outcomes must be read before any
promotion. The draw ending remains a separate conversion regression case.
2. **Learning second:** the current runtime's trained policy influences root
preferences; its neural leaf correction is disabled. Replaying these positions
does not update weights. The export supplies architecture-compatible 768 sparse
features, root-perspective best/played labels at both budgets and explicit mate
labels. Descendant positions require their own teacher labels; attaching the
root score to every later position would teach incorrect values.
3. **Targeted data third:** use the four actual losses, the drawn ending and
verified opposing replies. Preserve wins as controls. No additional broad GM
download is needed to address these diagnosed weaknesses.

Export: `runs/competition-review-20260908/learning-cases/verified-roots.jsonl` and
nine annotated PGNs beside it. Labels are development data; no new neural fit
or strength gain from fitting is claimed. Original PGNs remain unchanged.
The stopped overnight automation remains deleted; no long consistency study.


## Completed implementation trials

Both trials started independently from selected v1.53. No failed change was
combined with the other. All sources/inputs were frozen before launch; each ran
once under the same 14-position, one-second development screen. The stopped
cycle 38 and deleted automation were not resumed.

| Implemented change | Correctness / startup | Quality outcome | Decision |
|---|---|---|---|
| Root scout searches with full re-search of improvements | 9 oracle/source tests passed; 82.014s initialization; all probes legal and within bounds | More completed depth on 5/14 roots, but paired major errors 4 to 5 and mean regret 186/179 to 248/240cp; lost the Re6+ defensive repair; draw unchanged | Rejected |
| Queenless king approach to unsupported pawns | 4 tests, checking all nine PGNs and mirrors; 77.402s initialization; all probes legal and within bounds | All 14 selected moves unchanged; mean regret 186/179cp, four paired major errors, mate miss and draw unchanged | Rejected |

The scout review requested 0 new teacher nodes; the pawn-activity review
needed no new nodes because every move already had exact cached labels.
More search depth alone did not make this set better; a small generic king
activity score did not solve conversion. Do not increase its weight blindly.

**Recommended upload remains v1.53**, with its existing provisional status.
No v1.54, new neural weights or new match/Elo result was produced. The new source
implementations, original failures, evidence and verified teaching cases are
preserved for further work. No full games or long consistency study were run
for these two rejected changes.

The next useful engineering target is a bounded search of defensive alternatives
to the opponent's forcing threats, followed by inspection of the rook-ending
continuations that make Re1/Rf1 preferable to repetition. Those counterfactual
positions need independent value labels before descendant-network training.
This is more specific than adding more aggressive opening examples or broad GM
games, and avoids teaching that a pawn grab is good merely because the engine's
own imagined reply sequence looks favorable.
