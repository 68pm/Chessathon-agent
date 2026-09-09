# Second iteration: exact pawn extrema on v1.42

First iteration finished all four priorities: hashing had no speed gain,
exchange ordering had no required major repair, the small value fit worsened
unseen endpoint error, and current public field pages still list rounds73–75.
Keep all changes experimental and exact v1.42 selected.

The next efficiency target is the nested scan used to classify every passed
pawn at every classical evaluation. During the existing first board pass,
record the minimum white pawn rank and maximum black pawn rank for each file.
Passed-pawn status then requires three file comparisons instead of scanning
every forward square. Combine counts/extrema in one small array. No incremental
board metadata, bitset attack generator, scout, NN or changed evaluation formula.

Prove full classical-score parity on 1000 seeded positions and their mirrors,
with conversion on/off, plus edge/doubled/blocked-pawn cases and restoration.
Then 20 reconstructed development roots: 16 previous tactical roots plus two
largest distinct own field errors and two leader errors. Fixed250k-node ABBA
probes retain exact move/score/depth/node parity, with12s safety caps. Alternate
one-second clock probes too. Require >=1.05 median and aggregate CPU ratios and
no lower mean clock depth. This is a new mechanism on v1.42, not a rerun of the
previous combined bitset/pawn-mask prototype on a newer engine.

A passed efficiency gate still requires teacher review of timed choices,
read-only/startup validation and the saved short playing test before release.
Repeated scans of public completed games do not create independent strength
evidence, and no public per-game submission hash is available.
