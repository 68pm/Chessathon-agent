# Practical follow-through for cycle35

The frozen tactical gate passed: both previously missed mate-in-six positions
are recognized; original mistake repeats12->11 over21 clock probes; mean regret
258.71/276.67->236.86/255.76cp; no new paired200cp error or mate loss; the Bxf2+
root now chooses Qd3 within50cp at both budgets. This permits a small practical
comparison. v1.52 remains selected pending completion.

Copy the exact tested prototype to candidates/compiled-near-queen-checks-v1 and
build a deterministic internal ZIP without changing code or weights. Verify
every file and ZIP entry. Run strict read-only validation once at120000ms with
two legal calls, initialization<90s and memory<2GB. Only success permits exactly
two120+0.5 games against selected52, one in each color.

Use prepared starts.json index8: C86 Ruy Lopez, Closed Worrall Attack, Castling
Line after7...O-O. Parse the complete14-ply opening PGN and verify its starting
FEN and source hash. This is one prepared opening pair, not a resumption of the
cancelled consistency study.

Keep both scheduled outcomes regardless of the first result. Qualification
requires at least50%score with no operational or clock failure on EITHER side;
opponent failures cannot supply playing-strength evidence. Audit all moves,
both clocks, exact sources and outcomes. No added games to chase wins. Selection
and any numbered release require the completed review, with no calibrated Elo
claim from this pair.

Hidden Windows System PowerShell task at Normal priority4 from launch. Both
2048MiB free disk and768MiB physical RAM before validation, each game and every
fresh agent launch; wait at most20minutes, honor both STOP flags. No overlapping
teacher, training or JIT work. Freeze candidate, configs, wrappers and existing
harness dependencies. Preserve any failure and do not retry unchanged. After
the pair, inspect where actual mistakes first develop before further fitting.
