# Overnight checkpoint: first pass completed, 00:02 BST on9September

**Recommended upload remains v1.53.** No successor qualified during this first
pass. This is an intermediate checkpoint before the scheduled07:20BST report.
The next quiescence-cache experiment is separate and has no result in this report.

| Completed work | Measured result | Decision |
|---|---|---|
| Precomputed evaluator geometry | Isolated evaluation faster, full search slower; one baseline startup exceeded90s | Reject/incomplete balanced search test |
| Incremental hashing plus root scout | Fixed-work median CPU ratio1.00; no mean clock depth gain | Reject |
| Shallower initial quiet-check budget | Critical root completed depth1→2 but still chose Ra3; no100cp repair | Reject |
| Original rule-aware value network | Broad held-out MAE230.750→210.791cp; descendant MAE223.145→211.980cp | Reject10% descendant-improvement gate; only5.00% achieved |
| Latest own competition games | All174 own moves reviewed:86 positive,18 negative labels | Keep verified corrections and separate experimental policy checkpoint |
| Leader's completed games | All464 leader moves reviewed:427 positive,5 negative labels | Keep defensive examples; no simple exploit demonstrated |

The original781-input/64-unit value network was trained for20fixed epochs using
20,000 broad positions and101 independently labelled training descendants.
Validation used2,000 broad positions and31 descendants held out by source group.
Its scores are static errors, not Elo. It was not integrated into the agent.
[Detailed learning result](OVERNIGHT_VALUE_RESULTS_20260909.md).

The own-game policy checkpoint used96 examples(82good,14corrected), plus128anchors.
The separate leader checkpoint used144examples(140good,4corrected), plus128anchors.
Their one-epoch objectives improved only in-sample. Neither checkpoint was selected,
combined with the upload, or demonstrated stronger in games. Parent move rewards
were never used as unverified descendant-value labels.

## New competition evidence

| Public game | Our result | Main finding |
|---|---|---|
| [Round75, Istanbul's finest](https://aichessathon.com/game/35703c80-caf5-4613-95ab-7f83606d6d9f) | Loss, checkmate | Early14h3 conceded an advantage; later26Bf4 and31/33Kh3 worsened king defence.34Rxc5 took a pawn during the attack. |
| [Round74, Alpha Knights](https://aichessathon.com/game/ba876418-afb4-4bf3-9272-8331b869f184) | Win, checkmate | Five inaccuracies despite the eventual win; useful targets include more active rook play and preserving advantages. |
| [Round73, CCC](https://aichessathon.com/game/4b23f423-baf6-408d-9357-4adebc34b4e5) | Draw, repetition | Several middlegame advantages were given back.26Qxg5 cost303/308cp compared with Rb8. The eventual draw recovered from difficulties; don't penalise repetition regardless of position. |

These are **1W/1D/1L for an unverified competition build**, not new v1.53 results.
The last authenticated upload observation matched v1.41, but the public pages
do not provide per-game submission hashes. No competition upload was changed.

The leader's sampled rounds75/74/73 were all draws, including long rook endings.
The review found five inaccuracies in round75 and no confidently negative labels
in the other two at the declared80k/320k teacher budgets. Many later moves preserved
drawn positions. This does not prove perfect play, a strategy to beat the leader,
or that our agent played the leader. Public PGNs and source hashes are preserved.

## Retained local benchmarks

No new full local games were played in this first pass because the preceding
candidate gates failed. The latest pre-existing v1.53 E55 screen at120s+0.5s was
**2400:1W/0D/1L;2600:0W/1D/1L**. Across all eight exact-v1.53 rated games:
**2400:1W/1D/2L;2600:0W/1D/3L**. The highest clean nominal opponent beaten by
this exact build is2400, once. It has no2600 win or2800/3000 result.
Those handicap settings do not establish a calibrated rating.

All54 chronological release archives and the selected read-only ZIP remain
unchanged. Selected SHA256:
5747acec37da25ea79704e49d19e45bf23bd2af5842a14eaf66bf6ecf2791315.

Next priority is measured original-engine efficiency, preserving the same
evaluation, trained root policy, move legality, draw rules and game clock.
Failed candidates stay archived; the ongoing run ends with an honest07:20report.
