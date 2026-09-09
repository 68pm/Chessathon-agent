# Independently label the four persistent public-game failures

The selected-release probe confirmed that the latest retained engine still misses
the two Bxh7+ opportunities, chooses exf6 over Ng5, and misses ...Kg7 in favour of
attacking bishop moves. The move-hint experiment did not change those timed choices
and failed its median-efficiency gate. Repeating broader opening training or an
unchanged check-extension experiment would not diagnose the present limitation.

Freeze exact selected v1.55 on those four exposed roots, keeping full PGN history.
Compare eight forced branches: the originally played move and its verified
alternative at each root. Retain the established collector's bound of eight plies,
two million nodes and five seconds per branch. Remove root-policy preference only
inside this diagnostic worker to compare searched position values. Preserve the
unmodified playing files, compiled signatures and original policy on exit.

Follow only legal, exact transposition entries matching the actual repetition
context, halfmove clock and sufficient depth. Stop and report missing or nonexact
entries rather than inventing the continuation. Retain intermediate and endpoint
positions, plus four- and eight-ply teacher counterfactuals: at most 48 unique
label requests. Quiescence diagnostics retain their existing 100k-node/two-second
limits and preserve interrupted and mate scores.

Close the student process before independent Stockfish evaluation at 80k and 320k
nodes per position, at most 19.2 million newly requested nodes. Keep uncertain,
in-check, terminal and mate cases explicit. Compare static and quiescence residuals
to decide whether the next correction belongs in search or position evaluation.
No fitting, held-out claim, package selection or strength estimate is part of this
collection. Its new positions are development data. Keep capacity/STOP guards,
serial workers, owned-process watchdogs and the daytime cutoff.
