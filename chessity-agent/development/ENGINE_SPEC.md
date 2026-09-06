# Engine specification

## Stable interfaces

`agent.get_move(fen: str, time_left_ms: int) -> str` returns a legal UCI move when legal
moves exist. It returns `0000` on a terminal position because there is no legal move;
the referee ends such games before calling. Invalid FEN is a caller error.

`Search.run(board, seconds, soft=None, max_depth=64, known=None) -> Result` restores
the supplied board even on timeout. `Result` contains move, primary score, completed
depth, nodes (including quiescence), elapsed seconds and style score. An interrupted
iteration never replaces the last completed result. Depth zero means fallback only.

Evaluators return centipawns for the side to move. Mate scores are separate, near
30,000, and prefer faster wins/slower losses. The root style score does not alter the
reported primary score. It may choose a move within the configured tolerance, only
after exact re-search of near-tie bounds.

## Architecture

FEN -> legal fallback -> reconstruct observed history -> clock budget -> iterative
deepening -> negamax/alpha-beta -> quiescence -> evaluation -> best completed move.

Move legality, board updates and standard chess rules use `chess==1.11.2`. Search,
evaluation formulas, ordering, timing and the training framework were written for
this project with Codex assistance. No third-party search engine source is used.

The transposition table has 4,096 direct-mapped slots. Entries contain the position,
halfmove counter, reversible/search-history counts, depth, bound and normalised mate
score. The current implementation conservatively includes the full observed repetition
context rather than reusing scores across incompatible histories. This uses more memory
and misses some transpositions, a deliberate correctness-first tradeoff.

The clock uses `perf_counter`, a high-resolution monotonic clock. A soft budget stops
new depths; a larger hard budget interrupts internal nodes. A reserve and a 20ms
emergency fallback protect short clocks. Evaluation/move generation and OS scheduling
remain non-preemptible, so no absolute deadline guarantee is possible on arbitrary hardware.

## Neural contract

775 float32 features: 12x64 mover-relative piece squares, a constant mover channel,
four relative castling flags, legal en-passant availability, and normalised game phase.
Colour/rank canonicalisation makes colour-swapped mirror positions identical.
This differs from the source document's absolute side-to-move bit; the convention is
explicit and tested. File reflections are not used because castling can invalidate them.

Value model: 775 -> 128 -> 32 -> 1, clipped ReLU after each hidden layer, scalar
linear output. Label: tanh(mover-centipawns/600). Runtime inverse uses atanh after
clipping to +/-0.995. A 64-unit first-layer ablation and a training-only king-pressure
auxiliary output are also implemented. Export strips auxiliary outputs.

Training uses Dense forward/backward, explicit parameter gradients, Huber loss and Adam
in NumPy. Sparse runtime inference sums active first-layer rows. Weights are float32
NPZ arrays `p0..p5`, no pickle. Runtime modes are classical, neural, 20% hybrid, and
10%-30% phase blend. Only classical is currently selected in `runtime.json`.

## Constraints and unfinished optimisations

No aspiration windows, null move, LMR, check extensions, JIT move generation,
incremental NNUE, quantisation, ONNX export, books or tablebases are enabled.
Quiescence searches captures/promotions and all legal evasions when checked; it does
not expand arbitrary quiet checks. Emergency depth caps prevent pathological recursion.
Unknown pre-start game history cannot be reconstructed from one FEN. In-process history
tracks observed roots and our replies, reconnecting an opponent move when possible.
