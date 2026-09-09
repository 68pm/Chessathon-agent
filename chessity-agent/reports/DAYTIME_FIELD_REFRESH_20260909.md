# Latest completed public-game review

Five newly downloaded completed games were reviewed after the leader was identified
from the first-place row of the public leaderboard at 11:15 BST on 9 September.
The leader's bot name was PSL God Matt Bomer; its team name in PGN headers was
JBG fam. The team UUID matches the game-page side links. The two names therefore
refer to the same team, not different opponents.

| Reviewed side | Games | Moves | Positive signals | Negative signals |
|---|---:|---:|---:|---:|
| The Veritys | Two losses, rounds 78 and 77 | 85 | 35 | 12 |
| Leader | Loss, draw and win, rounds 79 to 77 | 329 | 227 | 3 |

All game histories were replayed legally. Stockfish reviewed candidate moves at
two node budgets, preserving mate scores and disagreements. Result and opponent
rating did not determine rewards. The policy fits are experimental and unselected;
none of this review changes the released v1.55 weights. Public games do not reveal
the uploaded source hash, so these losses cannot be attributed to exact v1.55.

In our round 78 loss, three consecutive chances for Bxh7+ were missed on moves
10–12. The verified alternative was an actual bishop sacrifice supported by
knight and queen follow-up, rather than a generic preference for aggression.
13.exf6 then changed a roughly equal teacher estimate into an approximately
three-pawn disadvantage; Ng5 was the stable alternative. The later Nc7/Nxa8 rook
grab did not address the threats around our exposed king. The useful targets
are sacrificial calculation, quiet defence and king safety while taking material.
[Round 78](https://aichessathon.com/game/ed1f0087-21bb-44ac-99e2-dd31c7a4d2ba).

In our round 77 loss, 18...Be6 was the first stable major error in the review.
The teacher preferred ...Kg7, allowing exchanges instead of the queen's entry
to h6 and a kingside attack. At the larger budget the comparison was -141cp
against -430cp from Black's perspective. This was already a worse position;
the alternative did not promise a win. Further inaccuracies in an already lost
position should not outweigh this earlier defensive turning point.
[Round 77](https://aichessathon.com/game/9cdd05d7-1511-4355-8b64-d773743f0be5).

The leader's drawn round 78 also exposed a conversion error: 130...g5 in check
gave up a teacher-estimated winning advantage, while ...Kg7 retained it. The PGN
clock showed about four seconds after the move. This is useful for testing our
defensive choices in late queen positions, not evidence that our executable can
beat the leader. Move number alone is not an endgame classifier; queen-containing
positions are tagged middlegame by the existing reviewer.
[Leader draw](https://aichessathon.com/game/5d694849-41bb-4f6b-8eaf-a37d95cdd515).

Before another behavioural change, replay selected v1.55 on the earliest reliable
turning points. It may already correct errors made by an older public submission.
Keep full move histories, test equal search budgets and preserve quiet alternatives.
Only actual searched descendants with independent labels belong in position-value
training. The failed value trials do not justify weakening the validation gate.
