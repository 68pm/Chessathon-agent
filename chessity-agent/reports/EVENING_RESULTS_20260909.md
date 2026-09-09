# Chessity improvement results — 9 September, evening

**Keep v1.56.** The only challenger that reached match testing scored **1 wins, 0 draws, 3 losses against exact v1.56** at120 seconds +0.5 seconds. It needed3/4 points. No v1.57 was created, no upload alias changed, and no new competition submission was made.

The four games used two preset openings, B12 Caro-Kann Advance Short and D48 Meran, with both colours. All ended by checkmate with no operational failures. The challenger was already ineligible after its third game; the fourth had started and was completed and reviewed. The2400/2600 stages were skipped after rejection. These results do not establish an Elo rating.

| Change tested | Measured result | Decision |
|---|---|---|
| Faster repetition query | Exact fixed-work parity; aggregate CPU speed ratio1.001, median0.988 | Reject: insufficient speed gain |
| Protect quiet pawn threats from reductions | More tactical regret and a new major error | Reject |
| Coordinated king-pressure evaluation | Fixed one example but caused other major errors | Reject |
| Queen-aware passed-pawn correction | About2% mean-regret improvement; below the declared10% gate | Reject |
| Exchange-aware ordering deeper in search | No mean-regret improvement | Reject |
| Tapered learned position evaluator | Broad development error improved8.5%, but separate White and Black checks worsened | Reject |
| King-step legal check combined with v1.56 buffers | About25% faster in aggregate fixed-work CPU tests; identical fixed-work decisions and unchanged tactical regret; failed actual games | Reject for release |

The learned evaluator was an original768-weight, symmetric middlegame/endgame position head fitted to13,386 existing labelled rows. It improved the broad development fit, but White mean absolute error rose95.6→115.4cp and Black43.5→68.4cp. It was never integrated into the playing agent. The three reserved Italian games remain unused. The first repetition preparation also had a setup/test failure; that failed attempt remains archived separately.

Every completed game went through Stockfish review: **183 challenger moves**, **90 positive labels** and **30 negative labels**. Experimental reward-policy outputs remain separate from the frozen playing agent. The correction pack contains **24 legal, independently supported alternative moves**; disagreements keep a null target. Root rewards are not substituted for searched-position value labels.

Corrections by phase: {'middlegame': 22, 'opening': 7, 'endgame': 1}. These are thresholded corrections, not a rating or an estimate of how often all moves are wrong.

The Caro-Kann Black loss exposed premature pawn pushes (9...b5 instead of...g6), a queen excursion (21...Qa3 instead of...Be7), and missed late defences. Raw learned policy preferences already favoured the verified alternative in three of four inspected major-error positions. That comparison does not measure full search activation or prove causality; it argues against assuming the policy alone is responsible.

In the Meran White loss,30.Rb6 allowed...Rd1 and lost a near-equal opportunity. At80k/320k requested Stockfish budgets,30.Rb8 evaluated0/−6cp, versus−350/−404cp for Rb6. The18.Be5 error had218/230cp regret but different teacher-best alternatives at the two budgets, so no single correction move was assigned. These cases support testing quiet defensive alternatives and rook activity before more broad opening data.

Next work should preserve the speed experiment but improve the decisions it exposes: inspect bounded defensive continuations from these failures, independently label their suitable descendant positions, and check a future evaluator on fresh games. Training on these four games makes their later replays development checks. Any successor still needs a short comparison against exact v1.56 before a release number, plus the declared rated gates.

The selected v1.56's earlier screen remains:2W/0D/0L versus v1.55,2W/0D/0L versus v1.53,0W/1D/1L at nominal2400 and0W/1D/1L at nominal2600. Those nominal settings are not measured Elo. Today's head-to-head result adds evidence for retaining v1.56, without proving it universally strongest.

Selected ZIP SHA256: `e0fb10c7ec482b93fe4bc20bfce7bd790bce78d163e5810a085a2223e795b99d`. Runtime remains read-only. Browser control was unavailable; the currently active competition submission was not verified. GitHub publication is recorded separately after push verification.
