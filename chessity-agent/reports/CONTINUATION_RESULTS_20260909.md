# Chessity: new-game analysis and opening curriculum, 9 September2026

**v1.56 remains the selected competition package.** The new games have been
downloaded and analysed, three position-value candidates trained and checked,
and a further search-allocation optimisation measured. None demonstrated enough
benefit to replace v1.56. No new release or competition upload was made in this
continuation, and no new competitive benchmark games were run for these rejected
candidates. The selected ZIP remains272750bytes, SHA256
`e0fb10c7ec482b93fe4bc20bfce7bd790bce78d163e5810a085a2223e795b99d`.

The public-game snapshot was taken around16:14BST. Our latest three completed
games were two losses and one draw. The public pages do not identify the uploaded
executable hash, so these games are not attributed to v1.56 or any other local
version. An older previously unreviewed round72 download was excluded from this
newest-game analysis. Three recent games of the leader observed at that snapshot,
Patzer2.4, were also reviewed: two wins and one draw.

| Our game | Main finding | Improvement target |
|---|---|---|
| [Round83, Black vs Stockfish's Nightmare, loss](https://aichessathon.com/game/c4f0ece0-b87b-4eda-b301-a4f0bd573af4) |19...Be4 worsened a nearly equal position. A deeper follow-up established that23...Re6 permits24.a5 and loses roughly344–371cp relative to the better searched defences. | Search quiet pawn breaks and defensive rook/bishop alternatives before committing. The alternatives differed between deeper searches, so no single replacement move was forced into the policy labels. |
| [Round82, White vs Jakub, loss](https://aichessathon.com/game/4614d5ac-4214-4430-aa97-9d76bfa652ca) | Several recoverable positions were mishandled:39.Nf1 and43.Nxe5 lost substantial value, then45.Kf4 allowed a much larger collapse. This was not simply an opening defeat. | Safe knight retreats, exchange calculation and king safety. In the specific43.Nxe5 position, Ne1 was a verified alternative; at45.Kf4, Ke4 resisted better. |
| [Round81, White vs CCC, draw](https://aichessathon.com/game/e0f6469d-b81e-47e9-b7cf-a7a90af90348) | This draw contained sizeable advantages that were not converted. At48.Ke3 the stronger continuation was d4; at55.Kxd4 it was Bd7. The earlier8.fxe5 also gave up much of the opening pressure compared with f5. | Pawn-break timing, bishop activity and conversion of advantages; avoid preferring a pawn capture or king move without comparing the resulting activity. |

The initial full review covered256 of our moves:173 supported positive moves and
21 negative examples, split1 opening /14 middlegame /6 endgame; the remainder were
neutral or uncertain. The deeper23...Re6 verification adds one separately recorded
major mistake. These are engine-supported labels, not infallible truth. In
particular, the smaller restricted searches initially missed the Re6 problem:
640000nodes evaluated it near−1.55pawns for Black, while2.56M and10.24M nodes
evaluated it at−5.34 and−5.56. Rewards were withheld while those estimates disagreed.

The four priorities were followed in order. First, reusing move storage in legal
move existence checks passed11 tests and96 ABBA comparison probes with exact
fixed-work decision parity. Its aggregate speed ratio was1.03046, below the
declared1.05 threshold, so it was rejected. Second, twelve bounded defensive
continuations at six new critical positions all reached eight plies. Exactv1.56
still preferred the played mistake over the independently suggested alternative
at all six diagnostic roots. This is development evidence, not a rating test.

Third,66 actual student/teacher continuation positions received independent value
labels;47 were suitable, and42 also passed the quiescence/static stability filter
used for fitting. Labels were attached to the actual descendant boards, with
their histories, rather than copied from parent evaluations. Static and quiescence
errors remained similar, indicating that capture-only continuation search was
not resolving much of the position-evaluation error in this sample.

The new fits used12000 broad training positions,1200 development positions,
including quiet endgames, the42 new descendant targets, and independently labelled
GM positions. Each was an original16-unit network, with no imported chess-engine
network. The table gives the same exposed White/Black colour checks; lower is
better, in centipawns. Those game groups became development data after the first
inspection, and were not presented as fresh holdouts again.

| Evaluator | White check,29 positions | Black check,16 positions | Decision |
|---|---:|---:|---|
| Selected classical evaluator |95.57|43.50|Retain |
| New GM/descendant fit |93.76|64.19|Reject Black regression |
| Add71 actual Black-to-move GM targets |93.89|60.17|Reject Black regression |
| Same data, two-perspective residual architecture |96.37|44.94|Reject colour checks |

The first fit reduced broad development squared error by8.95%, and reduced
error on its own recent training targets from115.38 to74.63cp. That was not
sufficient evidence of stronger play: it worsened unseen Black-position estimates.
The architecture change substantially reduced that regression but still failed
the unchanged no-regression checks. Five perspective/gradient tests passed. No
runtime integration, long consistency study or speculative Elo claim followed.
Three further unused Italian games were reserved for a later test but left
unlabelled when the development gates failed.

Fourth, opening preparation now focuses on actual preset structures. The collected
curriculum has17 master games with both players rated at least2500 in the source:
Petroff4, Catalan5, Italian6 and Closed Sicilian2. Fourteen are training games;
three were reserved initially. Fifteen came from recent TWIC archives and the
Closed Sicilians were already in the project. Raw TWIC files and labelled GM
histories remain local; they are excluded from GitHub evidence and agent packages.

For White, prioritise Italian/Ruy Lopez and Catalan structures, with proper
Sicilian preparation when those positions are assigned. For Black, prioritise
sound1...e5/Petroff play and Queen's Gambit/Nimzo-Indian structures, adapting to
White's move order. The actual new labelled module covers the four families above;
it has not completed a new Ruy Lopez or Nimzo-Indian module. These are serious
preparation choices, not promises of a forced advantage.
[GM Neiksans on White repertoires](https://www.chess.com/article/view/perfect-chess-opening-repertoire-white),
[Black repertoires](https://www.chess.com/article/view/perfect-chess-opening-repertoire-black).

Chessathon chooses the curated, near-level starting position, so our preferences
cannot automatically give the bot a better initial board. The useful learning is
central breaks, piece coordination, defensive resources and endings after that
position. No new Alien Gambit examples were added. The selectedv1.56 still retains
its earlier optional15cp Alien preference; it does not force a sacrifice and none
of the six inspected field starts matches it. Changes to that preference were
kept separate from these evaluator trials. [Competition specification](https://aichessathon.com/docs)

The most concrete next engineering target is the23...Re6 /24.a5 sequence: examine
quiet pawn threats and the available defensive continuations, then independently
label the reached positions at enough depth to resolve the observed horizon
error. The draw supplies complementary d4/Bd7 conversion targets. A further broad
opening-data dump would not directly repair these search and evaluation problems.

For reference, v1.56's previously completed short120+0.5 screen remains its latest
local playing evidence:2–0 against exactv1.55,2–0 against exactv1.53,0W/1D/1L
against nominal2400 and0W/1D/1L against nominal2600. These opponent settings are
not a calibrated Elo estimate for Chessity. There was no qualifying2600 win in
that screen, so no2800 pair was started. The recent public losses and draw above
are a different, version-unconfirmed dataset.

Operationally, per-file NTFS compression recovered678.3MB while verifying unchanged
contents for79 existing text files. No files were deleted and capacity reserves
were not reduced. All new bounded workers finished. The old automation remains
paused. Browser initialisation still fails with the missing-kernel-assets error;
the site's active submission hash has therefore not been re-verified. No new
candidate qualified for the user's authorised automatic upload in any case.
