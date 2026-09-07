# Independent consistency study 01 — v1.41

Requested explicitly on 7 September 2026 before starting a further engineering
iteration. Complete the fixed study even if early results are poor. v1.41 is the
selected frozen agent, SHA-256
`e4b66bd0f5a16418a49119c0547a818c3bb79a3c9e209b3eca7210907e072f63`.
Do not change its source, weights, time allocation or opening preference.

Budget: **256 games at 120 seconds + 0.5 seconds per move**, at most two concurrent
games. Each of nominal Stockfish 2400 and 2600 receives two 64-game blocks, with
32 distinct colour-paired opening groups per block. Use 64 new groups in total;
the same groups are used at both levels for comparability. Groups are disjoint
between blocks. Independence between opponent levels is not assumed or needed
for the summable error budget. Finish block 1 before block 2; alternate the level
order by pair, and play both colours. All results and failures remain visible.

Starting positions: use the existing legally replayed CC0 Lichess opening
dictionary in `data/three-phase-pack/opening-reference.tsv`. Before candidate
games, inventory prior local JSON match and diagnostic exposure, excluding this
new study. Exclude exact starting boards and colour mirrors already present in
that inventory, prior declared ECO starting groups, and ECO groups identifiable
from past opening setups/recorded boards. One position per distinct ECO code.
ECO labels are operational clusters; related theory can occur in different codes.
Neither this nor historical tests claim that every opening is unseen by every
historic root-policy training dataset. This is a new frozen performance test,
not a claim of a pristine training-data holdout.

Select using seed 2026090791 and fixed hash ordering, never candidate outcomes.
Eligible dictionary positions have 10–24 played plies, at least 24 pieces, no
check or game-over state and a halfmove clock below 10. Require full-strength
offline Stockfish estimates within +/-60 cp at both 20,000 and 80,000 nodes,
differing by at most 40 cp, with no mate score. Check at most eight eligible lines
per ECO and 512 total candidates (at most 51.2 million requested teacher nodes).
Retain all rejected selections and source hashes. If fewer than 64 groups pass,
stop preparation and report the shortage; do not weaken selection after seeing
the data. Both colours start from the same FEN and a fresh repetition history.
All teacher preparation must finish before the first candidate game.

Register attempts before the games: global consistency attempt 1 for 2400 and
attempt 2 for 2600. Each uses alpha = 0.05/(attempt*(attempt+1)), divided equally
between its two blocks. The existing conservative colour-pair Hoeffding gate
must pass independently in both blocks: more outright wins than draws plus
losses and a lower bound on outright win probability above 50%. That requires
at least 49 wins per block at 2400 and 51 per block at 2600 with this allocation.
Draws count as non-wins for that gate; report ordinary half-credit scores too.

No runtime failures, missing results, source changes or interrupted confirmation
can support a pass. Retain partial/interrupted results and never silently retry
them as clean evidence. An independent final review must verify every scheduled
game, legal move, clock, increment, opponent call, PGN outcome, frozen runtime,
source hash, starting-group exclusion and duplicate/mirror check. A process
interruption invalidates qualification; any subsequent recovery must disclose it.
Stop flags prevent dispatching more games; allow already active games to finish.
No training, teacher analysis or other development benchmarks during the study.

Keep the regular pool unchanged during the entire study. Only after the final
independent audit may a qualifying 2400 level be replaced with 2800, and a
qualifying 2600 level with 3000. These are engine handicap settings, not calibrated
human, FIDE or Chess.com ratings. Shared-computer load and related opening theory
limit statistical generalisation; report the recorded host load and uncertainty.

Three-priority review: engine changes are paused to measure the current champion;
learning is frozen to avoid adapting to this test; existing opening-reference data
supplies fresh performance groups, with candidate-independent balance checks.
After final results are reported, these games become development evidence for the
next engine/learning/data diagnosis. Existing results are not recycled into this
study and no games are added to seek a preferred outcome.
