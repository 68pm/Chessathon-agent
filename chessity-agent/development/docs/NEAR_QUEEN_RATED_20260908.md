# Four-game screen of released v1.53

Use the exact released v1.53 ZIP and source, verified against its Git tag. Play
exactly four serial 120s + 0.5s games: one as each color against nominal Stockfish
2400 and 2600. These are handicap settings, not calibrated human or site ratings.
No other opponent level or extra game is part of this screen.

Use prepared opening index9, E90 King's Indian Zinnowitz after 6.Bg5. Verify its
11 legal setup plies and final FEN from the saved PGN. This one prepared opening
does not resume the cancelled consistency study. Freeze all candidate, harness,
configuration and source hashes before launch. It is new comparison data; retain
every outcome, including flags and startup or illegal-move failures on either side.

Require 2048MiB free disk and 768MiB RAM before each game and immediately before
each candidate or opponent process. Wait at most20 minutes for capacity, honor
STOP flags and use a hidden Windows System PowerShell task at Normal priority4.
No teacher analysis, training or other JIT work overlaps these games. Initialization
remains at most90 seconds and inference at most2GB with read-only behavior.

Audit moves, both clocks, source hashes, outcomes and the exact four-game schedule
after completion. Then conduct bounded phase/mistake review before changing any
code or fitting weights. Engine improvements are first priority; useful descendant
learning is second; target only diagnosed data gaps third. Existing earlier exchange
evaluation errors and the new 26.Rd4 versus h3 warning remain known targets.
No result is inherited from v1.52, no Elo is inferred from this tiny sample, and no
extra games are added merely to obtain a win. v1.53 remains provisional meanwhile.
