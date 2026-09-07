# Cycle17: bounded root aspiration

Declared before running the pilot on7September2026. Base is selected41 only;
do not merge the failed queen/pawn, pruning or residual-value experiments.

Engine hypothesis: narrowing the root window around a previous completed score
can reduce work and finish a useful extra defensive ply. Use40,160,640cp half
windows from depth4, then the original full window. Widen fail-high and fail-low;
only commit a completed exact iteration. Keep the last completed choice on any
timeout/node limit. Disable narrow windows near mate scores. Preferences apply
only to ordinary scores and both child bounds are translated consistently.

Learning implication: policy/model bytes and leaf evaluation stay identical to41.
The prior failed replay pilot showed that fitting static values does not suffice.
This cycle isolates whether search can reach better consequences with those same
values. A later learning change requires new diagnosis, not more unchanged epochs.

Data: reuse the14 previously audited development roots in cycle15/all-roots.jsonl.
These include recent saved competition errors and endgame failures. No new broad
download is needed; exposed roots are diagnostic, not fresh strength evidence.

Correctness gate: root full-window parity against41, valid narrow upper/lower
bounds with preferences, board/history restoration, promotion, en passant, mate
scores, repetition, widening, and preserving completed work on interruption.
Only run after the serial baseline games and their audit finish; no concurrent
timed games, teacher or other own heavy compute.

Run exactly two alternating one-second/root passes per build: baseline1,prototype1,
prototype2,baseline2. Four processes,14 roots each; startup is outside the root
clock, recorded separately by each probe log. Preserve every measured pass; do
not repeat timings to obtain a favourable result. Cheap screening requires either
mean completed depth increasing by at least0.25 or fewer repeats of the recorded
error, without an aggregate increase in repeated errors. This is only a filter:
verify every selected move with cached or new80k/320k teacher evaluations.

Final position gate requires no new stable200cp error on any paired root/pass
where41's choice was below200cp at both budgets, no added paired mate loss, mean
capped regret no worse at either teacher budget, and either strictly improved
mean regret at both budgets or the predeclared0.25 mean-depth gain. Reject a failed
gate without ordinary games. Teacher nodes are requested only for new choices.

A pass is permission to freeze the candidate, validate read-only startup/memory/
legal play, and play the predeclared two-game colour pair against41. Require no
operational failure and at least50% pair score to proceed to one fixed eight-game
follow-up. Declare its release rule before results. No automatic rating or
promotion, no lengthy independent consistency check.

Operational amendment before any cycle17 measurements: the initial overnight
baseline failed during startup (three saved agent init losses, one opponent
handshake exception, no moves). Host free memory was observed near466MiB. Keep
that evidence. Subsequent games are serial with a768MiB pre-launch resource guard,
90s startup allowance for either participant, and preserved failure details. This
changes the local test protocol, not the bot or the120+0.5 move clock.

Correctness attempt1 is preserved under cycle-17/correctness-attempt-1. It ran
7passing/2failing cases in408.25seconds: the first test's deadline included cold
JIT compilation and expired; dynamically loading a second recursive JIT module
failed symbol resolution. No position timing gate or ordinary games ran.

Before attempt2, compile the tested core once outside position deadlines. The
full-window oracle now imports the unchanged inner search and retains the exact
original41 root function, with AST checks proving both relationships. This tests
the changed root bounds without loading a second recursive module into the same
Windows process. No engine logic, score tolerance, position set, gate threshold
or time budget was relaxed; cold initialization remains a separate runtime check.
