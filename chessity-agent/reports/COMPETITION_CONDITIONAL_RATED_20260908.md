# Small requested 2400 / 2600 screen, conditional 2800

After the new defensive/rook descendant work, freeze the selected candidate and
decision evidence. Use exactly one prepared opening pair at nominal Stockfish19
2400 and one at2600: candidate White then Black at each setting, 120 seconds plus
0.5 seconds per move, fresh initialization per game, serial CPU. Both clocks,
source hashes, legal moves and terminations must be audited. No rated result
exists yet for this screen; this document is a predeclaration.

Opening is source index11 in the existing frozen starts file, E55 Nimzo-Indian,
Gligoric System, Bronstein Variation after8...Nbd7. Replay its supplied PGN and
verify its FEN before creating the schedule. This is a small new requested
screen, not a resumption of the cancelled consistency study. The opening is
chosen now before this task's search and training results, not after wins.

Only a checkmate win against2600, with no failure on either side, triggers the
same two-game colour pair at2800. Draws or wins caused by opponent startup,
clock, crash or illegal-move failure do not establish that the engine beat that
strength setting. If no such2600 win occurs, record2800 as skipped. At most six
games, all outcomes retained, no play-until-win or long consistency checks.
These nominal UCI settings do not establish human or competition Elo.

If no new candidate passes a targeted quality gate, test the unchanged selected
v1.53 as explicitly requested. Identify its version in every result and state
that independent labels or rejected prototypes did not update its weights.
No candidate may be changed between the2400,2600 and conditional2800 games.

Require2048MiB disk and768MiB physical RAM before every candidate/opponent launch
and game, at most20 minutes capacity waiting. Serial hidden SystemPowerShell
NormalPriority4 from launch; no overlapping teacher, fitting or JIT jobs. New
STOP flags interrupt. Preserve all current archives and raw results. The deleted
overnight automation remains deleted; no live competition upload is performed.
