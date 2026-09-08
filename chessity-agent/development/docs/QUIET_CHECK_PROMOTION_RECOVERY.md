# Correct the two promotion fixtures, retaining eight passed checks

The corrected collection attempt executed all ten checks: eight passed in
52.80seconds, including quiet mate recognition, its one-layer limit, evasions,
terminal rules, castling/en-passant interruption and repetition. Two promotion
cases failed their python-chess validity assertion before exercising the engine.
Their original white pawn on g7 already checked the black king on h8 while
White was to move, an illegal fixture. This is a test-data error.

Use the independently checked legal position
`7k/5P2/6K1/8/8/8/8/8 w - - 0 1`, where f7-f8=Q is a non-capturing mate.
Run ONLY the two corrected promotion cases in a new output directory. Retain
the other eight passing checks, original failing XML/logs, unchanged candidate,
original targets and acceptance criteria. No completed position probe, game,
training epoch or performance gate has run for this candidate yet.

The gate validates the earlier eight passes plus the two new passes before
starting the originally declared baseline/prototype probes. Candidate code and
all data/budgets/criteria stay unchanged. This is a targeted fixture repair,
not a relaxed tactical requirement or an unchanged performance retry.
