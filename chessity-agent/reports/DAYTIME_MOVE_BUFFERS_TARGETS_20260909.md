# v1.56: defensive targets and the drawn rook ending

The completed 120s + 0.5s screen scored 2–0 against each of exact v1.55 and
v1.53, and one draw/one loss against each nominal 2400 and2600 setting. All478
candidate moves were reviewed. The34 negative move labels comprise24 middlegame
and10 endgame decisions; these include mistakes in wins. No calibrated Elo
follows from this small development screen.

Existing independent Stockfish root reviews identify concrete repair targets.
Scores below are from the candidate's perspective. Paired numbers are the
80k/320k-node review budgets, not two independent games.

| Game and decision | Existing root evidence | Next engineering question |
|---|---|---|
|2600, Black15...g4 instead of...Kg7|Best +3/−17cp; played −231/−241cp|Does bounded search inspect the quiet king move early enough, and does it recognise the knight activity after...g4?|
|2400, Black24...Be6 instead of...Bf8|Best +227/+225cp; played −235/−307cp|Why does the search prefer the active bishop move over the quiet defensive retreat as White prepares a rook lift?|
|2400, Black26...Qxb2 instead of...Bc5|Played permits mate in4 at both budgets; alternative −645/−636cp|Detect the immediate mating threat before accepting the pawn. The alternative avoids this mate line but does not restore an equal position.|
|2600, White53Rc5 instead ofh5, in the drawn game|Best −487/−486cp; played −598/−630cp|Improve endgame resistance and pawn/rook coordination. This evidence does not show a missed win, and the eventual draw should not itself be penalised.|

The mate after the pawn grab can be replayed legally:
26...Qxb2 27.Rg3+ Bg4 28.Rxg4+ Nxg4 29.Qh7+ Kf8 30.Qh8#.
This establishes a legal mating continuation, not a proof that every possible
defence is mated in four. The separate Stockfish mate estimates remain preserved
as mate estimates, without conversion to fabricated centipawn targets.

The repeated practical theme is selecting quiet defensive moves before the
opponent's attack becomes forcing. The reviews do not by themselves distinguish
move-ordering, insufficient search depth and position-evaluation errors; compare
actual searched continuations before selecting an engine change. More aggressive
opening examples would not directly resolve these decisions.

The next student/teacher diagnosis stopped before preparation because storage
fell below the existing2048MB reserve. Its failed supervisor has no stages and
produced no new labels or training. RAM was above the existing1400MB minimum.
The reserve was not lowered and no training evidence was deleted.

A lightweight legal-replay step is complete in
`runs/daytime-20260909/move-buffers-unlabelled-queue-01/queue.json`: four roots,
three game groups,16 teacher-PV descendants, including one exact checkmate.
Every descendant has a null value target and is ineligible for finite training.
Full histories, source hashes and terminal outcomes are retained. No engine was
launched, no new teacher nodes were spent and no model was updated. These are
exposed development positions, not student-search leaves or a fresh holdout.

Keep v1.56 selected while capacity and browser access recover. Future value
learning still requires independent descendant labels, the existing suitability
filters, game/FEN/mirror overlap checks and a short practical comparison before
any replacement is activated. GitHub publication of v1.56 is verified; competition
activation is still unverified because browser control cannot connect.
