# Sound preparation for Chessathon's actual starting positions

Chessathon assigns a curated, near-level position. Our opening preferences cannot
choose or overwrite that starting board. Preparation should improve the moves
after the preset, including the opponent's strongest replies. No opening promises
an advantage against accurate defence. [Competition specification](https://aichessathon.com/docs)

The immediate curriculum contains17 master games: Petroff4, Catalan5, Italian6,
Closed Sicilian2. Both players in each game are rated at least2500 in the source.
Fifteen games come from recent official TWIC archives; the Closed Sicilians were
already in the project. Three fresh complete games were reserved before any value
labels. Raw TWIC downloads stay local under the source's personal-use notice.
[TWIC archive](https://theweekinchess.com/twic)

| Family observed in recent games | White's preparation | Black's preparation |
|---|---|---|
| Petroff, own round83 | Coordinate development and central pressure; check whether an advanced knight or pawn can be maintained before collecting material. | Complete development, support the central structure, compare active rook defence with a premature bishop move. The specific round83 target is19...Re8 versus19...Be4. |
| Catalan, own round82 and leader round82 | Make the g2 bishop and central pawns work together; compare maintaining tension, c5 and captures. Preserve knight retreat squares and king safety during exchanges. | Challenge the centre with a prepared ...c5 or ...e5 when legal and sound; resolve queenside tension without losing coordination. Calculate White's long-diagonal threats. |
| Italian, leader round81 | Prepare central expansion while keeping the king safe and pieces coordinated. Choose pawn breaks after checking the resulting exchanges and counterplay. | Meet central pressure with active development and a justified central break. Avoid treating every kingside move as an immediate attack. |
| Closed Sicilian, own round81 and leader round83 | Compare f5 with exchanges that release central tension. Later, calculate the d-pawn break and bishop activity before king moves or pawn grabs. | Counter central and kingside space with concrete central/queenside play; retain defensive resources and avoid unnecessary weaknesses around the king. |

These are training questions for independently analysed positions, not automatic
move rules. The recent draw's8.f5,48.d4 and55.Bd7 are specific verified alternatives
at those exact boards; they are not instructions to push the same pawn in every
similar position. The displayed reaching lines in curriculum metadata are legal
explanations of the position families, not recovered organiser move histories.

For later expansion beyond these observed presets, prioritise White's Italian /
Ruy Lopez after1.e4 e5 and Catalan / Queen's Gambit structures after1.d4; prepare
Open Sicilian or Rossolimo structures when assigned. GM Arturs Neiksans identifies
these as serious repertoire choices. This task's new labelled games cover the
four families above; it has not completed a new Ruy Lopez or Rossolimo module.
[White repertoire discussion](https://www.chess.com/article/view/perfect-chess-opening-repertoire-white)

For Black, sound1...e5 structures, the Petroff, and Queen's Gambit / Nimzo-Indian
structures are sensible broader preparation targets. The precise response depends
on White's move order; a Catalan cannot be treated as though White had committed
to Nc3. Sicilian presets require their own treatment. The immediate reason to
study the Closed Sicilian is that the competition actually assigned it, not a
claim that it is White's strongest possible opening.
[Black repertoire discussion](https://www.chess.com/article/view/perfect-chess-opening-repertoire-black),
[GM Bryan Smith on the Closed Sicilian](https://www.chess.com/article/view/vassily-smyslov-and-the-closed-sicilian)

The selected v1.56 still has its previous optional15cp Alien preference; this is
not a forced opening and none of the six newly inspected field starts matches
that line. The new value trial isolates evaluator changes, preserving the selected
release. No new speculative gambit examples were added. A future preference
change should be measured separately from this evaluator experiment.

Learning is numerical: independently evaluate the actual positions, represent
them in the network's side-to-move piece-square features, and train corrections
to the classical position score. Do not claim the network has learned a paragraph
of chess theory merely because that paragraph was written. Frozen validation and
timed search determine whether the labelled examples help.
