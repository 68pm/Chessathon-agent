# Cycle20: useful depth with the recovered startup

Declared before this comparison. v1.51 is selected as a startup revision of
v1.41; playing evaluation and weights are unchanged. The first cycle17 position
output failed with ENOSPC and is preserved as an unusable timing attempt. Its
nine correctness cases did pass. This separately declared comparison changes
both tested builds to the recovered startup and records initialization and
per-position outer wall time explicitly. No old failed output is overwritten.

Engine need: quiet defence and useful search depth. The latest played loss at
nominal2800 contains37Kf1 instead of verifiedKg2, a674/734cp error. Prototype20
combines the already tested cycle17 aspiration mechanism with v1.51's completed
warmup and plain diagnostics. From depth4, use40/160/640cp windows followed by
the full window, translating both bounds for root preferences and retaining
only completed exact iterations. No evaluation, policy, time-allocation,
endgame-table or reduction change is bundled with it.

Learning need: hold every weight fixed to isolate search. The completed replay
capacity review showed many requested corrections outside the available125cp
contribution. Do not repeat that failed fit or increase its blend. A later fit
needs a capacity-compatible objective and matched control, after search diagnosis.

Data need: retain all14 exposed cycle15 verified finite-error roots and append
all three latest stable finite>=200cp errors from the startup-recovery games.
Namespace the three new IDs, reconstruct full supplied game histories, and
retain the exact80k/320k teacher references. These17 positions are development
data, not independent strength evaluation. No new broad data download.

## Fixed comparison and stopping rule

Freeze both source manifests, all17 roots, source/configuration and this plan
before the first measurement. The prototype core is byte-identical to the
tested aspiration core; its driver differs only in the package import and the
same warmup used by v1.51. Validate AST parity around that integration without
re-running the unchanged expensive correctness cases.

Run four fresh processes in order baseline1, prototype1, prototype2, baseline2.
One second per root, policy preference disabled equally, reconstructed history,
all search tables reset before each root. Log every result and completed
aspiration iteration. Record import/initialization separately and require<=90s;
require a legal move, completed depth>=1, restored board/history and outer wall
time<=1.25s per root. Each process has a180s hard stop, so a native initialization
hang is terminated even without an in-process diagnostic watchdog. Any operational
failure stops the gate and is preserved; do not retry unchanged timing attempts.
Both disk>=2048MiB and available RAM>=768MiB must pass before each process or
teacher work, with at most20minutes waiting. No other heavy work or games overlap.

Cheap gate: mean depth gain>=0.25 ply OR fewer repetitions of the original
mistake, with no increase in aggregate mistake repeats. Only if this passes,
review the selected moves at80k and320k using original labels/cached choices
where applicable. At most68 choices (27.2million newly requested teacher nodes
before cache reuse) are possible. Require no newly stable200cp paired error,
no new mate loss, no higher mean regret at either budget, and either strictly
lower regret at both budgets or the declared depth gain. Preserve both passes;
no thresholds or positions change after results.

A pass permits packaging and strict read-only validation, then exactly two
120+0.5 games versus v1.51 from the next unused prepared opening index6 in both
colours. Require>=50% score and no candidate operational failure before deciding
on a small further comparison. A gate pass alone does not select a new upload
or establish higher Elo. A failure means critique the mechanism and keep v1.51;
do not resume the256-game consistency study or extend tests until a win.
