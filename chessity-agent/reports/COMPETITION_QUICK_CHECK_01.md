# Four-game competition diagnostic — 7 September 2026

The selected v1.41 played this fixed short check at 120 seconds + 0.5 seconds.
It completed between 17:24 and 17:36 UTC, including post-game analysis.

| Opponent setting | Wins | Draws | Losses |
|---|---:|---:|---:|
| Stockfish 19, nominal 2400 | 0 | 0 | 2 |
| Stockfish 19, nominal 2600 | 1 | 0 | 1 |

All four ended in checkmate, with no runtime failures. The v1.41 win over nominal
2600 was with White. Each opponent received one preselected opening played in
both colours; this small, narrow sample is useful for development, not a rating
or proof of consistent strength. These are local games, not dashboard results.
The earlier independent confirmation remains a separate dataset.

The complete source, PGN, legal-move, clock and outcome audit passed. All 190 own
moves were screened with the offline teacher; suspicious choices were rechecked
at 80k and 320k nodes. The first warning in the three losses occurred once in the
opening and twice in the middlegame. The two stable transitions from a defensible
position into a losing one were 21.Rf3 against 2400 (61 seconds still available)
and 27...gxf2 against 2600 (41 seconds available). Teacher alternatives were Rfe1
and ...Re6 respectively. The other loss first showed a large error with 12...f5;
its first transition across the chosen losing threshold remains unresolved.

The immediate priority stays calculation and tactical judgement. The capture
ordering experiment in IMPROVEMENT_CYCLE_09.md tested a specific mechanism on
existing v1.41 errors and failed its gate, so it did not proceed to matches. No training,
promotion, rating update or opponent replacement follows from this short check.

The user has supplied the competition dashboard and clarified that older matches
used older agents; only the latest 2–3 use more recent bots. Match versions must
be verified or recorded as unknown. After sign-in, the 21-game summary and latest
three complete game records were saved. See COMPETITION_RECENT_GAMES.md for the
separate real competition findings and the limits of the version mapping.

Evidence: quick-check-01--review.json, phase reports and the two complete match
reports under evidence/improvement-20260907. The selected ZIP is unchanged v1.41,
SHA256 e4b66bd0f5a16418a49119c0547a818c3bb79a3c9e209b3eca7210907e072f63.
