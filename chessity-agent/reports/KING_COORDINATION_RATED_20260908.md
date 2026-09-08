# Four-game rated screen for frozen v1.52

After the clean1W0D1L pair and completed81-move teacher review, v1.52 is a
provisional practical recommendation. Its rated-opponent performance is unknown.
Run exactly four games of the same candidate: nominalStockfish2400 and2600,
one game of each color per level, serially at120 seconds plus0.5 seconds per move.
Keep all four regardless of early results. No extra games until a win and no
pool retirement or rating calibration from this small screen.

Use the previously prepared opening at index7 in consistency-01/starts.json:
B73 Dragon Classical/Battery after9.Qd2. Parse its17-ply PGN and verify the exact
FEN. Earlier explicit opening configurations contained no B73 when selected.
One new prepared opening pair is reused across the two levels, not a resumption
of the cancelled consistency study. Keep weights, source, clocks and choices
frozen; the ZIP is72604b1b50c2e22200b70068d8ab98d25a96b586a20278ae465c464cd77ee2c8.

Use existing nominal UCI handicap settings and ordinary game harness. Audit every
move, both clocks, source, opening assignment and outcome. Distinguish checkmate
wins from opponent failures. Games supply performance information and targeted
mistakes; they do not update parameters or grant rewards automatically.

Before each game and each candidate/opponent process require2048MiB disk and
768MiB free physical RAM, with at most20minutes of waiting. Use one hidden
Normal-priority local controller and respect STOP flags. No other JIT, teacher,
training or heavy chess work overlaps. Preserve any interruption rather than
restarting the same failed screen blindly.

After all four outcomes, report exact W/D/L per level and the strongest opponent
actually beaten by this build. Diagnose the first verified deterioration before
choosing new engine work or compatible descendant training. Existing missed24.Nf6+
and15...Nxf8 are already useful targets; additional broad GM data is not required.
This small practical screen follows the user's priority to improve quickly.
