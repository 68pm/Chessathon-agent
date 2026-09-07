# Cycle 03 — selective calculation after the confirmed search gain

v1.41 is the incumbent after 23W/1D/0L against v1.14, 3W/4D/1L at nominal2400,
and 0W/3D/5L at nominal2600. The consistency target is still unmet.

The completed rated-game audit screened826 own moves, finding8 >=200cp errors
stable at80k/320k nodes, plus83 mate-scored rows. A separate classification found
one new teacher-forced-mate transition, in an already badly losing position; this
is finite search evidence, not an exhaustive proof. Several material errors came
with28–77 seconds remaining. Examples include a losing rook exchange, queen-side
pawn grabs during a king attack, and an endgame conversion opportunity.

The successor-value pilot accepted4 of8 pairs (8 endpoints), quarantining4 for
unstable or out-of-range endpoint scores. Keep those labels for future replay.
This sample alone is too small to justify another broad neural fit or claim general
tactical learning. Static MSE already failed to predict a clear playing gain in
cycle02. More targeted coverage is needed before repeating that experiment.

Next hypothesis, declared before testing: the existing original conservative
late-move reduction branch can allocate more calculation to promising continuations.
It reduces a late quiet move by one ply only at depth>=3, after at least four legal
moves, outside check, and when the move does not give check. Captures/promotions
are not reduced; a move that exceeds alpha is searched again at full depth.
Enable this one existing option in a frozen table-enabled copy of v1.41; keep
all weights, evaluation, clock settings and opening preferences identical.

Gate: terminal/legality/clock checks, strict read-only package check, then paired
one-second probes on the8 newly audited errors and the mate transition. Require
no increase in repeated original errors and no lower mean completed depth before
spending a match budget. Top-one agreement is only diagnostic; alternatives may
also be good. These positions are development material, not fresh confirmation.

If the gate passes, run8 colour-paired development games against v1.41 and4 each
at nominal2400/2600,120+0.5, at most2 concurrent games. Use previously exposed
development openings, record all outcomes, and audit the result before proceeding.
Do not add games to chase a win. A later promotion needs a new independently
declared confirmation against v1.41, with fresh groups and the next alpha allocation.
The previously rated C10/C53/C67/D10 groups are retired from fresh confirmation.

Gate result: the control repeated9/9 original choices and averaged6.56 completed
plies of depth; the reduction candidate repeated7/9 and averaged7.56, with teacher
top-one agreement1/9 versus0/9. Both used1s per position. The candidate avoids the
rook-exchange choice in game13 and finds the teacher move in game14, but still misses
the rook-and-bishop conversion. Alternative moves need independent assessment before
being called correct. Its16 compiled-core tests and strict read-only package checks
passed. The frozen folders differ only in runtime.json's reduction flag.

After the fixed16-game screen, the queue audits its8 rated games and verifies at
most16 further successor pairs (at most12.8M requested endpoint-label nodes).
Review all evidence and data coverage before another fit or independent confirmation.
v1.41 remains selected during this development experiment.

The eight-game comparison is complete: **1W/5D/2L**, score43.75%, no runtime
failures. This provides no evidence to promote the reduction flag despite its
better diagnostic depth. The frozen build is archived publicly as experimental
**v1.42**.

The complete rated screen scored **2W/0D/2L at nominal2400** and **1W/2D/1L at
nominal2600**. Game5, with White after the exposed Ruy Lopez setup, ended in a
verified checkmate win over Stockfish19 configured with UCI_LimitStrength=true,
UCI_Elo=2600, one thread, and both120+0.5 clocks. All16 games were independently
replayed with source/clock/outcome checks and no runtime failures. This is the
first ordinary nominal2600 victory in this improvement programme, not a calibrated
rating or evidence of consistent wins. The complete tiny sample includes the loss.

The error audit found5 stable >=200cp errors in304 own moves;38 rows had mate
scores requiring separate interpretation. The successor pilot accepted4 of5 pairs,
adding8 endpoints. This remains development data. Several errors occurred with
33–75 seconds remaining, so spending more opening-data or broad-fit budget would
not directly address the calculation failures. The next isolated search experiment
will reuse board-matching move hints while retaining history-specific score bounds.
No promotion: the incumbent comparison still gives no gain. v1.41 remains selected.
