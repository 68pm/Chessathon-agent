# The missed refutation is a forcing sequence of checks

**Kh1 was correct. The engine misses the mate after the subsequent greedy rook
capture.** Cycles 33 and 34 refine the earlier hypothesis without changing v1.52.

After `...Bxf2+ Rxf2 ...Qe1+ Rf1 ...Qe3+`, all three legal replies were analyzed.
Scores are from White's perspective:

| Reply | Student depth3 | Student depth5 | Teacher80k | Teacher320k |
|---|---:|---:|---:|---:|
| Kh2 | -505 | -360 | +453 | +496 |
| Kh1 | -378 | -364 | +544 | +544 |
| Rf2 | -1204 | -1202 | Losing mate7 | Losing mate7 |

The student's original Kh1 reply matches the teacher's best defense. At depth3
it then expects `...dxc5 Qe7`, and at depth5 `...Qxc5 Qxf7+ Kh8 Qf6+`, both scored
as favorable to Black. Six bounded student probes all completed with exact TT
traces; initialization63.576s, total39,168 nodes. The teacher requested1.2M nodes.

A separate four-position teacher review requested2.8M nodes and verified the
refutation at both80k/320k budgets:

- After Kh1, Black's best defense is `...Rf2`, still White+568/+567.
- Both `...dxc5` and `...Qxc5` instead permit **mate in six for White**.
- After `...dxc5`, the student's Qe7 loses (-668/-680). Qxf7+ begins the mate.
- Even the endpoint after `...Qxc5 Qxf7+ Kh8 Qf6+` remains a forced mate in four
  for White. It must not be assigned an ordinary positional training target.

One verified line after the pawn capture is:

`Qxf7+ Kh8 Qf6+ Kh7 Qe7+ Kg8 Qxd8+ Kg7 Qf8+ Kh7 Rf7#`

The continuation mixes checking captures with four quiet checks. The selected
quiescence search explores captures and check evasions, but omits quiet checks
when the attacker is not currently in check. Its two normal-search check
extension credits were already spent on the earlier checks. This exposes a
specific search horizon problem: the capture can look profitable when the
remaining checking sequence is not searched.

The next engine hypothesis is a bounded continuation of quiet checks when a
queen has approached the opposing king, with explicit checking credits,
unchanged terminal rules, complete legal evasions, state restoration and node
bounds. This must be tested against the verified mating sequences and the
existing21-root regression set before any selection. It is not a license to
repeat the failed older quiet-check pilot unchanged or claim that more checking
moves will always improve strength.

Learning should preserve these verified mate outcomes and opponent continuations;
fitting a favorable student leaf alone would reinforce the wrong root choice.
The separate exchange-ending value errors from cycle32 remain unresolved.
Existing targeted data is sufficient for the next experiment.

Both hidden tasks exited successfully and were removed after checking that no
owned chess processes remained. Every source/history/budget and outcome is
preserved. No new game, training update, package, Elo estimate or opponent win
is claimed. The reported mates are teacher analyses, not wins played by Chessity.
See [cycle33](IMPROVEMENT_CYCLE_33.md), [cycle34](IMPROVEMENT_CYCLE_34.md), and the
[complete evidence](evidence/forcing-check-diagnosis-20260908/manifest.json).
