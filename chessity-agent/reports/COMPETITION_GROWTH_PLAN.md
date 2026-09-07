**Chessity: draft plan for faster competition improvement**

Prepared 7 September 2026 from the conversation, current source, completed local
experiments and the latest saved competition games. This is a proposed next-work
plan. The current ten-game schedule continues unchanged; drafting this plan does
not launch another training run or replace the selected agent.

The recommended approach is to keep v1.41 as the competition baseline, identify
the earliest costly decisions in its actual games, and turn each recurring problem
into one measured engine change or a small verified learning dataset. Package an
improvement promptly when its practical evidence supports it. The objective is
better play before the deadline, not a long rating-certification programme.

Subsequent user steering: analyse the newest build's games locally; the request
to use Claude was cancelled. The ten-game test is now complete and is recorded in
[its review](COMPETITION_TEN_GAME_REVIEW.md). It added two startup failures, so
startup reliability is an immediate engineering priority. The user-requested
bounded mistake-replay loop was implemented and completed after that test. Its
final snapshot improved the replay count from1/7 to2/7 but failed the held-out
gate and was not promoted; see [cycle16](IMPROVEMENT_CYCLE_16.md). Other proposals
below remain a draft. This result supports prioritising the search-to-learning
connection over simply repeating the same training for more epochs.

**What the project already tells us**

The selected build is `candidates/compiled-qsearch-endgames-v1`. Its own compiled
search uses classical position evaluation, the trained player-policy preference
with a 10cp limit, optional Alien preparation and elementary endgame tables.
`residual_value` is false and `value_blend` is zero. Its trained policy can influence
close root choices, but the experimental learned leaf evaluator is not enabled.
See [the selected runtime](../versions/v1.41/source/runtime.json).

Learning inside search has already been implemented in the experimental 768â€“32â€“1
residual network with incremental evaluation. Reuse this work rather than claiming
it still needs to be built from scratch. Full-strength residual corrections harmed
the earlier incumbent comparison; v1.47's quarter-strength correction was more
promising but did not demonstrate a reliable improvement. The specialised paired
training pilot retained only 18 pairs, split into 12 training and six validation
pairs across five opening families. That is a narrow basis for generalisation.
See [cycle 6](IMPROVEMENT_CYCLE_06.md) and [cycle 7](IMPROVEMENT_CYCLE_07.md).

The recent real competition games contain middlegame mistakes even in wins.
For example, 26.Kf1 surrendered an advantage that Rc1 preserved. Earlier traces
showed two different failure types: a useful defence appeared only at greater
search depth, while a promotion ending was misjudged even after the engine saw
the promotion. They require different remedies. The v1.47 phase review likewise
located the first losing transition in the middlegame in three of four losses,
although all four games finished in the endgame. The remaining loss was unresolved.
See [competition findings](COMPETITION_RECENT_GAMES.md),
[cycle 14](IMPROVEMENT_CYCLE_14.md) and [cycle 15](IMPROVEMENT_CYCLE_15.md).

Faster search and fewer errors on exposed positions have not automatically produced
stronger match results. Preserve these measurements and failed ideas. Do not merge
all versions, average incompatible weights or keep repeating a failed test until
it passes. Earlier broad pruning, capture ordering, caching and hash experiments
remain evidence, not a list of features to switch on together.

**Three possible routes, in priority order**

| Route | First concrete work | Data needed | Proposed effort cap before a decision |
|---|---|---|---|
| A â€” improve the current engine | Trace a few recurring first-error positions; test one search, clock or evaluation mechanism | Existing own-game positions, full history, clocks and verified alternatives | About 1â€“3 hours for one bounded candidate, including a small check |
| B â€” make learned evaluation useful | Reuse the incremental residual evaluator; improve the coverage and targets of a narrow training pilot | Verified better/worse continuation pairs plus broad replay examples | Half a day to one day for an initial controlled pilot; stop earlier if search decisions do not improve |
| C â€” targeted outside chess knowledge | Fill a demonstrated tactical or positional gap from themed puzzles or relevant GM positions | A filtered subset of existing data first; outside data only for missing themes | About 30â€“90 minutes for a small extraction/verification pilot, conditional on data availability |

These are planning estimates and effort limits, not promises of a stronger upload
or a particular Elo. Start with A. B and C support a diagnosed weakness; they are
not three expensive jobs that must run for every small revision. Keep analysis
and training off the machine while the current timed games run.

For route A, first determine whether the correct defence is found with more search
or is still undervalued. If search is the limit, inspect completed depth, wasted
re-searches, node cost and move stability. A possible new experiment is a narrow
root search window around the previous iteration's score, widening it when needed;
its clock cost and correct handling of policy bonuses and mate scores must be
measured before using it. It is a hypothesis, not a diagnosed fix. The engine
already has iterative deepening, principal-variation search, history and killer
ordering, so adding those names again would not be progress.

Time allocation is another conditional candidate: use logged decision instability
to spend more of the existing budget on difficult moves and less on forced ones.
First measure whether missed defences occur with usable time remaining. Do not
simply raise every move's budget and create time trouble later. If instead the
engine sees the continuation but misvalues it, target the evaluator's demonstrated
material or king-safety error. Test related legal positions as well as the original
failure before spending an ordinary-game budget.

**What data is most useful to supply**

| Priority | Data or file | How it would be used |
|---|---|---|
| 1 | Latest competition PGNs, per-game runtime logs, and exact upload version/hash if available | Find first deterioration, hidden mistakes in wins, server timing and build attribution |
| 2 | Own mistakes paired with verified better continuations | Teach the consequences of a decision, not just imitate a move |
| 3 | Defensive tactics and endgame conversion examples | Address king defence, recaptures, trapped pieces, promotion prevention, rook activity and pawn endings |
| 4 | GM positions matching the observed pawn structure or material situation | Supply relevant strategic alternatives; retain the player's identity as provenance rather than a quality label |
| 5 | Sound aggressive and Alien Gambit examples | Preserve the preferred style among adequately evaluated choices, without forcing a sacrifice |

The recent dashboard games are already available; no new user upload is required
to begin. Future PGNs and their runtime logs are the most useful additional files.
Preserve full initial FEN, legal history, played move, clocks, final outcome, game ID
and build provenance. Mark inferred version mappings explicitly. Older-version
games remain useful training material, but their results are not the current
agent's rating. The competition provides a downloadable log with initialization
and move timings alongside each PGN. It also uses curated, roughly balanced starts,
which reduces the value of investing heavily in one move-one opening repertoire.
See [the official match documentation](https://aichessathon.com/docs).

For an initial learning pilot, aim for 32â€“64 distinct critical decision points
from multiple games and position families, using the already collected mistakes
and the current batch when its audits finish. This is a provisional upper budget,
not a reason to invent examples or generate many extra full games to meet a quota.
For each root, verify the actual choice and a better alternative, then label their
continuations once forcing play settles. Two endpoints from one root are one
related family, not two independent examples. Start with fewer if that is all the
verified evidence supports; expand only where useful targets are still missing.

Reuse the existing broad dataset as the majority of training replay. A reasonable
initial proposal is about 70% broad positions, 20% targeted decision/continuation
examples and 10% matched puzzle or strategic examples, with per-game and per-root
exposure caps. These proportions are an untested starting recipe, not an optimal
mix. Keep original source-game and opening-family partitions, group related
continuations together, and remove exact/mirrored duplicates across partitions.
Reserve a small family-disjoint set before fitting. Do not treat the exposed
positions that motivated a correction as fresh strength evidence.

The existing Lichess material should be filtered before downloading more. If a
theme is missing, its open puzzle database offers FENs, UCI solution lines, themes
and game references under CC0. Use defensive moves, intermezzos, exchanges and
promotion/endgame themes where they match our failures. Apply the first listed
move before presenting the puzzle to the solver, as its documented format requires.
Puzzle difficulty is not the agent's playing Elo. See
[Lichess's dataset format](https://database.lichess.org/#puzzles).

Use Carlsen, Hikaru, Gotham, Witty and other existing game collections to extract
positions with those same needs. A GM's chosen move still needs verification; a
human win is not proof that every earlier move was good. Theory documents help us
design features and labels. Merely copying prose or PGNs into an agent ZIP does
not update this network.

**How learning should change**

Train the value of positions reached inside search and the ordering of the two
verified continuations, keeping all comparisons in the original mover's
perspective. Preserve correct terminal/draw handling and avoid using unresolved
mate scores as ordinary finite evaluations. Reuse cached stable 80k/320k labels;
spend extra teacher work only on new or unstable branches. Keep a matched model
without the new targeted signal to distinguish its effect from another training run.

Before expanding the architecture, compare errors by material and king context.
The current compact inputs contain piece placement, so useful interactions must
be learned through a very small hidden layer. If the new data cannot improve a
specific relationship, test one small explicit context feature group or a compact
king-relative representation. Keep inference cheap enough to preserve useful
search depth. King-relative features and incremental updates are established NNUE
design ideas; the Stockfish documentation is conceptual reference here, not a
proposal to ship its engine or pretrained weights. See
[the NNUE feature discussion](https://official-stockfish.github.io/docs/nnue-pytorch-wiki/docs/nnue.html#halfkp).

Winning against a stronger opponent should count in candidate selection. For
training, verified move/position quality should be the primary signal: otherwise
we reward 26.Kf1 just because the opponent later lost. A bounded game-result term
can be a later auxiliary experiment, with its own control. Do not give every move
in a won game a positive target or repeatedly play until one win appears. Mixing
evaluation and game-result signals is described in the
[NNUE training discussion](https://official-stockfish.github.io/docs/nnue-pytorch-wiki/docs/nnue.html#using-results-along-the-evaluation);
the appropriate balance for this bot remains unmeasured.

The current running games perform testing and then analysis. They do not modify
the model's weights while playing. Accepted examples must enter an explicit
offline fit; a separately frozen ZIP then contains the resulting weights and code.

**A short iteration that can produce usable uploads**

1. Review the completed ten-game results, including each prior-version opponent,
   and the first verified errors. Keep this one-opening sample's limited scope.
2. Choose one recurring mechanism and a small set of relevant positions. For every
   iteration write three lines: the engine hypothesis, the learning implication,
   and the specific data gap or why existing data is enough.
3. Implement one candidate derived from the selected baseline. Use meaningful
   correctness checks and fixed-node plus real-clock position comparisons. Track
   verified regret, missed defences, preservation of advantages, completed depth
   and wall time. A lower training loss or a higher nodes-per-second number alone
   is not the success criterion.
4. Reject poor ideas at that cheap gate. Use a two-game colour pair for a preliminary
   ordinary-game screen. For a promising competition candidate, use one fixed small
   follow-up, typically eight games: four against the selected baseline across two
   opening families and two each against nominal2400/2600. No long consistency check.
5. Review the complete planned results, runtime reliability and tactical evidence
   together. Declare the practical release rule before those games, including how
   an inconclusive result is handled. Do not expand the schedule until the result
   becomes favourable. Keep the prior best if the evidence does not justify a switch.
6. Package a justified improvement, validate read-only inference, preserve the old
   ZIP and publish the chronological version plus its actual results. Give the user
   the exact recommended download; keep live competition submission separate.

Combine two changes only after testing them individually, and test the combination
because search, evaluation and clock behaviour interact. Keep Alien optional.
Prioritise preventing a large recurring middlegame mistake over improving an
opening preference that many curated starts never reach.

**Suggested remaining schedule**

Finish the present test and diagnosis first. Use 8 September for the best-supported
small engine changes and prompt practical releases. On 9 September, run the narrow
learning pilot only if the collected targets and runtime budget support it. Use
10 September to compare the strongest surviving changes and prepare the best
combined candidate, without a speculative wholesale rewrite. Have a final checked
download ready with time for competition validation before the published
11 September 11:00 submission cutoff. These are planning priorities, not a reason
to postpone a clearly improved upload or promise 2600 strength by a date. The
[official submission information](https://aichessathon.com/docs) specifies that cutoff.

Keep each experiment small, preserve the failed evidence, and use game quality
and practical results to decide the next action. Consistently beating a nominal
2600 opponent remains an aspiration; this plan does not establish that rating.
