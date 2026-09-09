# Daytime development checkpoint — 9 September 2026, 08:24 BST

The selected upload remains exact **v1.42**, SHA256
`114c1688a63d4039d7965670fcab0891bec24d4835dacafa8698e22d0c01f48b`.
No new version has qualified or been submitted. The user has explicitly authorised
automatic submission of a demonstrated stronger successor; website validation and
the newest active submission must be observed before claiming success.

## Completed work

| Experiment | Evidence | Decision |
|---|---|---|
| Isolated incremental hash, unsigned revision | 13 tests passed; exact fixed-node parity; aggregate and median CPU ratio1.0 | Reject: no measured efficiency gain |
| Bounded exchange ordering | 16 tests passed; mean regret139.69/172.81 ->134.81/167.19cp at80k/320k teacher budgets | Reject: modest average gain without required100cp repair |
| Original eight-unit position-value fit | Broad error improved; target MAE175.12 ->106.50cp; unseen descendant MAE218.43 ->232.14cp | Reject: unseen value error worsened |
| Public field refresh | Latest visible completed games remained rounds73-75, already reviewed;638 own+leader moves reused | No redundant download or teacher work |
| Passed-pawn extrema optimisation | 16 tests passed;20roots,160ABBA rows; aggregate CPU speedup1.05605, median1.05806; exact fixed-node decisions | Pass efficiency stage |
| Pawn candidate clock-choice review | Equal finite mean regret134.47/163.32cp; no major mistake or mate regression | Pass tactical stage |
| Pawn candidate read-only package |18.565s startup;2legal calls;221.29MiB peak; filesystem mutations blocked | Pass local upload checks |

Failed initial hash boxing and two field-parser attempts are preserved separately.
All consumed source, preparations and outcomes remain immutable. Neither the
rejected value weights nor exchange code entered the selected upload. The pawn
candidate changes classical passed-pawn classification cost while preserving
evaluation scores; its eight-game screen has started and is incomplete.

## Next evidence

One colour pair each against exactv1.42, exactv1.53, nominal2400 and2600, at120s+0.5s.
Each game receives history-aware independent Stockfish review and an experimental
policy fit; playing weights stay frozen. Only a clean played2600win allows one2800
pair. The saved promotion rule requires >=1.5/2vs42, >=1/2vs53 and no operational
failure, alongside the passed earlier checks. This is a short development screen,
not independent Elo calibration or a long consistency study.

The earlier exactv1.42-v1.53 comparison remains3W/1D/0L. Historical nominalv1.42
results remain2400:2W/0D/2L and2600:1W/2D/1L; no new rated result is claimed here.

## Field and access

Our largest existing field corrections concern king defence and risky captures.
The leader's errors include checks where a quiet alternative scored better.
These support defensive search and endgame work. Public results do not identify
each uploaded executable version. The public own-team snapshot showed1638 and
18W/7D/15L; the leader snapshot showed2770 and26W/17D/9L. These are site snapshots,
not local estimates for the selected archive. Sources: [own team](https://aichessathon.com/team/b650ca5f-caff-48e7-932a-3ccdb6ab6332?from=lb),
[leader](https://aichessathon.com/team/10021bb5-71a5-4b10-bde5-14e1f667501a?from=lb).

Both available browser/native control runtimes failed before connection with a
missing kernel-assets path. Public read-only data was accessible. No authenticated
submission was made or claimed. The run continues through16:00BST with a15:40
heavy-work cutoff; the active job and recovery steps are recorded in the journal.
