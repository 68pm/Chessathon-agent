# Confirmation progress — 7 September 2026, 09:14 UTC

**chessity-agent v1.41 finished 23 wins, 1 draw and 0 losses against v1.14** in the
fixed 24-game comparison at 120+0.5. Twelve distinct starting groups were played
with both colours. All games passed frozen-source, legal-move, clock, increment
and outcome replay checks. There were no runtime failures.

Its score was 97.9%. The predeclared conservative lower bound on paired score was
58.7%, above the 50% comparison threshold. This assumes independent opening groups
and stable conditions; it does not calibrate a human/site rating. The one draw was
a threefold repetition in a pawn-heavy opposite-colour-bishop endgame.

The eight games each against nominal 2400 and 2600 are now running. The full
promotion rule also requires those scheduled games and reliability checks to finish.
Consequently, v1.14 remains the official download for now. The stronger head-to-head
result is encouraging, but consistent 2600 strength has not been established.

After the rated matches, the existing queue will review promotion eligibility and
analyse errors. A separate bounded successor-data pilot waits for that work to finish,
then verifies at most 16 played/preferred continuation pairs for the next learning
experiment. No training or teacher analysis runs during the confirmation matches.

The repository preserves all 42 versions through v1.41, with chronological commits,
annotated tags and matching source/weights. The failed v1.35 preflight is explicitly
archival. Other experiments are not automatically promoted by version number.
