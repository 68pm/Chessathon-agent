# Evidence-driven improvement programme — 7 September 2026

User authorises continued autonomous engineering, targeted data acquisition, training and
2400/2600 evaluation towards consistent wins. No guaranteed strength or completion time.
Current incumbent after confirmation: **v1.41**, `candidates/compiled-qsearch-endgames-v1`,
SHA256 e4b66bd0f5a16418a49119c0547a818c3bb79a3c9e209b3eca7210907e072f63.
Original incumbent v1.14 remains preserved, SHA256
6d287209c28bba520a21ef49261af99543a167fb192ce15513102c883c503a56.
New candidates must now be compared against v1.41. The completed confirmation's
rated groups C10, C53, C67 and D10 are retired as development material.

## Loop

1. Audit the first decisive errors in the incumbent's games using full available history.
2. Record a concrete mechanism and falsifiable hypothesis before each experiment.
3. Fix search/evaluation correctness and efficiency; train only when a learning signal
   addresses the measured failure. Frozen previous candidates are never modified.
4. Use correctness/perft, tactical and endgame checks before expensive matches. Freeze
   source and weights. Run both colours from balanced openings at 120+0.5.
5. Compare with the incumbent, then nominal Stockfish 2400/2600. Retain the incumbent
   unless independent confirmation supports promotion. Analyse failures, then repeat.

The first engineering candidate will implement our own mailbox move generation/search
using the competition's explicitly permitted Numba runtime, with compilation at import,
no native binaries shipped and no disk cache. Development uses a separate environment.
The learned evaluator experiment follows the measured search pilot; offline teacher
labels are permitted, pretrained chess networks and third-party engine implementations
are excluded. Existing player material is already sufficient to start. Search for new
public source material only for a specific coverage gap and retain provenance.

Old benchmark games used for diagnosis become development data. Repeated final tests
must use new held-out opening groups and report every completed game, including losses.
Do not increase an ongoing frozen match to chase one victory. Each cycle has a declared
budget; continuing means a new documented hypothesis/cycle, not unbounded repeat epochs.
Initially screen with eight comparison games and four per rated setting; promising builds
receive larger fixed confirmation schedules. A small screen cannot certify strength.

Consistency target: a frozen build must pass two independent 64-game 2600 blocks at the
real clock, with more wins than draws+losses and a lower confidence bound above 50% on
outright win probability. Use paired-opening uncertainty and account for repeated cycle
testing. Also confirm against 2400 and diverse independent opponents. Settings are not
human/site Elo; no official rating is inferred. No runtime failures are acceptable.

Local CPU only, no paid services. At most two concurrent match games; teacher labelling
must not run during final performance confirmation. Training and test partitions remain
separate. Stop flags STOP_TRAINING / STOP_BENCHMARK are honoured. Record checkpoints,
criticism, rejected ideas and actual results. Scheduled continuation should stay quiet
unless there is a meaningful result, failure, resource limit or required user action.

## Three needs reviewed in every iteration

The user reaffirmed the priority order: better engine code first, better use of
training second, and targeted data after a diagnosed gap. Every future cycle must
include the [three-part review](IMPROVEMENT_REVIEW_TEMPLATE.md), recording the
evidence and decision for each need. The learned descendant-position evaluator
exists experimentally; it must prove a playing gain before replacing v1.41.
Prioritise the remaining verified threat-calculation and conversion errors when
the current fixed calibration screen is complete. Preserve its schedule and
weights while it runs. Do not resume broad data collection or unchanged fitting
merely to keep the programme busy.

Rules rechecked: https://aichessathon.com/docs and https://aichessathon.com/terms,
2026-09-07. Numba 0.67.0 allowed; Python 3.12, one CPU, 2 GB, 90s init, 50 MB ZIP
uncompressed, read-only inference. No Daily Five material is accessed.

## Next measured efficiency hypothesis

The 18-position, one-second development probe searched about5.31M nodes with compiled
classical evaluation and3.84M with the first residual network. These are shared-host
diagnostics, not isolated performance guarantees. The new network's full piece-square
sum repeats at every leaf. Maintain two incremental hidden accumulators, one per colour,
updated on make/unmake, so the exact same trained weights need less work. Verify numerical
parity across legal move sequences, promotion, castling and en-passant; compare fixed-node
choices and wall-clock throughput before another match. No additional fit is needed for
this experiment. Existing frozen matches continue against the original full-sum network.

The incremental probe recovered only about5% nodes, with unchanged top-one/error-repeat
counts. A second source inspection found that every quiet quiescence node constructs
and validates every legal move merely to test whether at least one exists. An early-exit
legality predicate should preserve stalemate handling and the search tree while avoiding
unneeded make/unmake work. Test terminal/special-move cases, compare exact fixed-node
results against the frozen compiled control, then measure throughput before matches.
