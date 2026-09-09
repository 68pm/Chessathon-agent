# Prove the quiet mate before assigning a position value

The two forced Bxh7+ continuations both reached positions with legal Qh3# after
eight plies. Independent Stockfish labels and python-chess confirm mate in one.
The selected capture-only quiescence search instead returned -140cp and -91cp.
These are mate cases excluded from value training, not finite residual examples.

Test a narrow terminal detector on the preserved fast-legal parent. At the first
quiescence boundary, when our king is not checked and the enemy king has left its
first two ranks, examine legal quiet queen moves to empty squares adjacent to that
king. Generate only those geometric queen paths. After making a candidate, verify
our own king's safety, check on the enemy king and absence of every legal reply.
Return a mate score only after that proof, restoring all state. Otherwise continue
the existing capture-only leaf search unchanged. This adds no recursive quiet-check
extension and does not reward an attractive but unproved attack.

Validate the two real positions and colour mirrors, independent legality and mate
oracles, pins, off-scope kings, random continuations and exact state restoration.
Existing rule priority, hash/halfmove handling, root policy and weights stay intact.

Then compare the exact fast parent and prototype on the existing nineteen roots
plus the two mate endpoints. Use serial warmed ABBA one- and three-second searches
with a five-million-node cap. All moves must be legal and meet timing limits.
Independent 80k/320k teacher review must show lower mean finite regret at the
three-second budget, no new stable 200cp mistakes or mate losses, and at least one
of the two Bxh7+ root choices repaired at three seconds in both prototype repeats.
The two leaf mates must be recognised in correctness tests. This behavioural
trial is judged by decision quality; a speed gain is not presumed.

Only a passed tactical gate proceeds to the short 120+0.5 match screen against
selected v1.55, v1.53 and nominal 2400/2600, with conditional 2800. Retain every
failed attempt. No fitting or promotion from diagnostics alone. Keep capacity,
STOP, owned-process and daytime-deadline guards; no concurrent heavy jobs.
