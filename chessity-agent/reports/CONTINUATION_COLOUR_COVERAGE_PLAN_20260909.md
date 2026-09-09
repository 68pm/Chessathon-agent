# Repair actual-colour sampling, preserving the rejected first fit

The first16-unit curriculum fit improved its White-position reservation slightly,
but a frozen16-position Black check worsened43.5->64.19cp MAE. This is a diagnosed
coverage failure. Preserve all weights/results; no runtime integration or matches
for that candidate. Add independently labelled actual Black-to-move positions
from the14 training games, at plies21/29/37/45/61/81. Keep the earlier White
training labels and recent independently labelled student descendants. Do not
negate a White evaluation to invent a Black-to-move label.

The previous three reserved games are now exposed development data. Keep both
their White and Black positions out of training. Use them only as an additional
post-fit development gate (each colour's MAE and >=200cp count no worse than
classical). Do not select new hyperparameters or blend after viewing this gate.

From the already downloaded official TWIC archives, choose the three lowest
full-game hashes among unused Italian games with both players>=2500 and at least
84 legal plies. Exclude duplicates of any of the17 existing curriculum games or
the earlier1838-game GM corpus. Reserve before labels; no result or teacher-score
selection. These reservations test a single opening family, a stated limitation.
Keep raw PGNs local. Sample20/21/32/33/44/45/56/57/68/69/80/81, both actual colours.

Use exact/mirror exclusion against all mainline positions in both new and exposed
reserved groups. Add at most84 Black training labels and36 fresh reserved labels;
maximum48M requested nodes at80000/320000 per position, normal finite/stability
filters. Retain every exclusion and uncertainty.

Reuse the first fit's broad rows, seed2026090917, architecture16 units,24 epochs,
fixed signed outputs, Adam and80/20 gradient mix. Only the added actual Black
targets and required duplicate exclusions change. The original development
gates apply unchanged. Then the exposed White/Black gate above. Only on success
freeze and label the new Italian reservations: at least6 eligible per colour,
each colour's MAE and >=200cp count no worse. No fresh holdout retuning.

Only a passing candidate receives the previously declared runtime numerical,
timed tactical and short practical match checks. This trial creates no release
or strength claim by itself. All serial, capacity/STOP/deadline unchanged.
