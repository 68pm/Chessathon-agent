# Fresh wins still expose middlegame errors

Direct public observation at 13:23 BST identified leader UUID
429a581d-e7fc-41e3-a915-2895b01d7d0b (Poincare / Gladiator). It downloaded and
legally replayed five new completed games, deduplicating prior field06 data.
Submission hashes are unverified; these are not measurements of a known release.

Chessity won rounds 79 and 80 as Black by checkmate. The teacher reviewed all
66 own moves, rewarding 35 and penalising six, all in the middlegame. Round79's
13...g5 lost roughly 264/288cp against ...e5 at the two budgets. In round80,
14...Qc5 lost 461/508cp against ...Qb6 and 18...g6 lost 216/218cp against ...exf4.
The later ...Be4 and ...Rd7 also had supported better alternatives. A win does
not make these earlier decisions correct.

The leader's latest three completed games scored one win and two draws. All295
moves were reviewed, with252 positive labels and one endgame inaccuracy. Neither
draw contained a negatively rewarded move in the reviewed leader decisions;
the draws do not justify indiscriminate anti-draw penalties. Keep uncertain
alternatives and mate labels as such. All feedback-policy fits are unselected.

The five complete reviews contain361moves,287positive labels and7negative labels.
Next value targets require suitable independently labelled descendants, not
copies of these root rewards. No runtime weights, selected ZIP or site submission
changed in this refresh. Source URLs and hashes are preserved in field-07.
