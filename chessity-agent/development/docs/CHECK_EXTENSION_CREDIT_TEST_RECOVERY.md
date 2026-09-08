# Repair the Python credit-observation test

The first cycle23 test run completed8passing cases and2failures in104.47seconds.
Compiled zero-credit score/node parity, transposition-budget separation, terminal
rules, interruption restoration and real repetition all passed. Both failures
were confined to the Python spy that observes recursive extension credits.

The spy bypasses Numba's typed function boundary. A uint64 position key returned
from a compiled helper becomes a Python int; at an irreversible move the history
context therefore reached the Python XOR expression as an untyped large int,
causing an OverflowError. Compiled recursive calls retain uint64 semantics.

Normalize only the spy's context argument to uint64 modulo2^64 before invoking
the Python body, matching the compiled signature. Keep all credit assertions,
engine code, game histories and gate criteria unchanged. Run ONLY those two
corrected observer cases in a separate output and validate the prior eight
passes by XML hash. Preserve the first report and original test source. No
performance probes, teacher calls, training or games ran in the failed attempt.
