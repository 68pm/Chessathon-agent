# Bounded development rematch, declared before games

The search pilots have not qualified a release. The latest conservative check
prefilter preserved fixed-node results but improved aggregate CPU time only
7.406%, below its declared 10% requirement. Earlier compiler signature repair
improved startup and preserved fixed-work results, but failed its one-second
clock-choice review. Those failures remain recorded and neither build is selected.

A specific diagnostic exception is warranted: play at the actual 120s + 0.5s
clock to identify current search errors and obtain fresh game-separated learning
targets. One-second position probes do not reveal full-game time allocation or
the stage in which this engine loses. No new full games have been played in this
overnight run. The public recent games also lack verified submitted-build hashes.

Use the frozen coalesced-search-01 prototype: v1.53 search logic and weights with
the compiler signature repair. Attribute its results separately from the exact
v1.53 release. Choose the predeclared D65 start, offset 2, with both colours.
Start with one pair at nominal 2400. A completed clean played win permits one
pair at 2600, then 2800 and 3000 under the same rule. Any operational failure in
the pair prevents ascent. Finish each pair, preserve all losses and draws, and
never repeat a level to seek a win. Each pair including post-game feedback has a
45-minute bound. Reserve that whole bound before the 06:40 BST cutoff.

All games use scripts.feedback_matches. Every completed game receives
history-aware Stockfish review and a separate experimental policy checkpoint;
the playing weights remain frozen. Inspect independently supported errors by
opening, middlegame and ending, including missed chances in wins and draws.
Root action rewards are not descendant position values. If value training is
revised, reserve distinct source games before constructing its targets.

This diagnostic does not override a failed gate, promote a release, certify Elo
or change the competition upload. v1.53 remains the selected fallback. Source,
candidate manifests, complete results and review/checkpoint hashes are preserved.
