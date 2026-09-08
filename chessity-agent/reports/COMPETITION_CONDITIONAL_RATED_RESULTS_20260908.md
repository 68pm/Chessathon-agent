# v1.53: requested 2400 / 2600 screen and conditional 2800

This screen used **exact v1.53**, with the existing weights and playing code.
The preceding work independently analysed defensive alternatives and the drawn
rook ending, and exported safe descendant labels. It did not train or release a
new model. These match results belong to v1.53, not to a hypothetical improved
network, and are a small local screen rather than a calibrated Elo estimate.

One colour pair per setting, 120s + 0.5s, from the predeclared E55 Nimzo-Indian
opening after 8...Nbd7. Every game, source, move, outcome and both clocks was
audited. The 2800 pair required a checkmate win against 2600 with no failure on
either side. All outcomes are retained; no play-until-win or long consistency
study was performed.

| Nominal opponent setting | Wins | Draws | Losses | Failures on either side |
|---|---:|---:|---:|---|
| 2400 | 1 | 0 | 1 | 0 |
| 2600 | 0 | 1 | 1 | 0 |
| 2800 | — | — | — | Not run: no qualifying 2600 win |

| Setting | Candidate colour | Result | Termination | Played plies after setup |
|---|---|---|---|---:|
| 2400 | White | Win | checkmate | 71 |
| 2400 | Black | Loss | checkmate | 133 |
| 2600 | White | Draw | threefold_repetition | 175 |
| 2600 | Black | Loss | checkmate | 93 |

Highest nominal setting beaten by checkmate in **this screen**:
**2400**. Failures on either side: **0**.
A single win would not establish consistent strength at that setting.

The recommended ZIP remains the existing provisional v1.53, SHA256
`5747acec37da25ea79704e49d19e45bf23bd2af5842a14eaf66bf6ecf2791315`. No v1.54 or neural-weight change is claimed. All 54 archived versions
remain intact. See the accompanying defensive/rook report for the new 37-position
review, 15 eligible quiet learning targets and the reasons further value-learning
work needs a compatible objective rather than blindly fitting the old residual.
